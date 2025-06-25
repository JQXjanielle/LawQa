from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from rdflib import Graph
from pathlib import Path
from preprocessing.preprocess import preprocess_and_stem
from googletrans import Translator
import re, json

app = Flask(__name__)
translator = Translator()

# ✅ Load KG
KG_PATH = Path("C:/Users/60128/Documents/NLP2/Data/knowledge_graph.ttl").resolve().as_uri()
graph = Graph()
graph.parse(KG_PATH, format="ttl")

# ✅ Load fine-tuned model
MODEL_PATH = Path("C:/Users/60128/Documents/NLP2/Source/Models/flan_t5_malay_qa").as_posix()
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH, local_files_only=True)

# ✅ Load dataset.jsonl
def load_dataset_jsonl(path):
    dataset = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            sec = obj.get("section", "").strip()
            act = obj.get("source", "").strip().lower().replace(" ", "_")
            if sec and "body" in obj and act:
                key = f"{act}_sec_{sec}"
                dataset[key] = {"context": obj["body"]}
    return dataset

DATASET = load_dataset_jsonl("C:/Users/60128/Documents/NLP2/Data/dataset.jsonl")

# ✅ Type keyword mapping
TYPE_KEYWORDS = {
    "denda": ["denda", "didenda", "kompaun"],
    "penjara": ["penjara", "dipenjara", "jara"],
    "tajuk": ["tajuk"],
    "kandungan": ["kandungan", "isi utama"]
}

SPARQL_PROPS = {
    "denda": "http://example.org/hasFine",
    "penjara": "http://example.org/hasJailTerm",
    "tajuk": "http://example.org/hasTitle",
    "kandungan": "http://example.org/hasContent"
}

def detect_type(question):
    q = question.lower()
    for t, keywords in TYPE_KEYWORDS.items():
        if any(k in q for k in keywords):
            return t
    return "kandungan"

def extract_section(question):
    patterns = [
        r'seks?yen\s*(\d+[A-Z]?)',
        r'section\s*(\d+[A-Z]?)',
        r'第\s*(\d+[A-Z]?)\s*条'
    ]
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def get_acts_for_section(section):
    query = f'''
    SELECT ?source WHERE {{
        ?s a <http://example.org/traffic-law#Statute> ;
           <http://example.org/traffic-law#sectionNumber> "{section}" ;
           <http://example.org/traffic-law#sourceFile> ?source .
    }}
    '''
    return list({str(row.source).strip() for row in graph.query(query)})

def query_kg(section, q_type):
    prop = SPARQL_PROPS.get(q_type)
    if not prop:
        return None
    query = f'''
    SELECT ?value WHERE {{
        ?s a <http://example.org/traffic-law#Statute> ;
           <http://example.org/traffic-law#sectionNumber> "{section}" ;
           <{prop}> ?value .
    }}
    '''
    results = graph.query(query)
    for row in results:
        return str(row.value)
    return None

def get_malay_label_for_section(section):
    query = f'''
    SELECT ?label WHERE {{
        ?s a <http://example.org/traffic-law#Statute> ;
           <http://example.org/traffic-law#sectionNumber> "{section}" ;
           <http://www.w3.org/2000/01/rdf-schema#label> ?label .
        FILTER (lang(?label) = "ms")
    }}
    '''
    results = graph.query(query)
    for row in results:
        return str(row.label)
    return None

# ✅ Main API
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    original_question = data.get("question", "")
    lang = data.get("lang", "ms").strip().lower()
    context = data.get("context", "")
    user_act = data.get("act", "").strip().lower().replace(" ", "_")

    print("🟡 Original question:", original_question)

    if lang != "ms":
        translated = translator.translate(original_question, src=lang, dest="ms")
        question = translated.text
        print("🌐 Translated Question:", question)
    else:
        question = original_question

    q_type = detect_type(question)
    section = extract_section(question)

    print("🟢 Type:", q_type)
    print("🟢 Section:", section)

    # 1. Disambiguate Acts
    act = user_act
    if section and not act:
        matched_acts = get_acts_for_section(section)
        if len(matched_acts) > 1:
            return jsonify({
                "source": "ambiguous",
                "section": section,
                "acts": matched_acts,
                "message": f"Multiple acts found for Seksyen {section}. Please select one."
            })
        elif matched_acts:
            act = matched_acts[0].lower().replace(" ", "_")
            print("📘 Matched Act:", act)

    # 2. Direct KG answer
    if section and q_type != "kandungan":
        kg_answer = query_kg(section, q_type)
        print("🔵 Direct KG:", kg_answer)
        if kg_answer:
            return jsonify({"source": "kg", "answer": kg_answer})

    # 3. Load context from dataset
    dataset_entry = None
    if act and section:
        key = f"{act}_sec_{section}"
        dataset_entry = DATASET.get(key)
        if dataset_entry:
            print("✅ Loaded entry with act + section key.")

    if not context.strip() and dataset_entry:
        context = dataset_entry["context"]
        print("🟢 Loaded context from dataset.jsonl")
    elif not context.strip() and section:
        raw_context = query_kg(section, "kandungan") or ""
        context = preprocess_and_stem(raw_context)
        print("🟡 Fallback context from KG")

    # 4. Generate model answer
    prompt = f"Arahan: {question} Berdasarkan konteks berikut. Konteks: {context}"
    tokens = tokenizer(prompt, max_length=512, truncation=True, return_tensors="pt")
    output = model.generate(**tokens, max_length=128)
    model_answer = tokenizer.decode(output[0], skip_special_tokens=True)

    print("🧠 Model Answer:", model_answer)

    if lang != "ms":
        back_translated = translator.translate(model_answer, src="ms", dest=lang).text
        print("🌐 Translated back:", back_translated)
        return jsonify({"source": "model", "answer": back_translated})

    return jsonify({"source": "model", "answer": model_answer})

if __name__ == "__main__":
    app.run(debug=True, port=5001)







