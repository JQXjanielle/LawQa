import os
import json
import re
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from rdflib import Graph
from preprocessing.preprocess import preprocess_and_stem
from googletrans import Translator
import requests

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Load translator
translator = Translator()

# Load RDF knowledge graph
KG_PATH = Path("Data/knowledge_graph.ttl").resolve()
graph = Graph()
graph.parse(KG_PATH, format="ttl")

# Load model
MODEL_PATH = Path("Source/Models/flan_t5_malay_qa").as_posix()
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH, local_files_only=True)

# Load dataset
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

DATASET = load_dataset_jsonl("Data/dataset.jsonl")

# Define keyword types
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

# Utility functions
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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_language', methods=['POST'])
def set_language():
    session['language'] = request.form['language']
    return redirect(url_for('home'))

@app.route('/home')
def home():
    lang = session.get('language', 'en')
    return render_template('home.html', lang=lang)

@app.route('/chat')
def chat():
    lang = session.get('language', 'en')
    if lang == 'ms':
        title = "Sistem Pertanyaan Undang-undang Memandu Malaysia"
        placeholder = "Tanya soalan anda di sini..."
        submit_text = "Hantar"
        back_text = "Kembali ke Pemilihan Bahasa"
    elif lang == 'zh':
        title = "马来西亚驾驶法规查询系统"
        placeholder = "请输入你的问题..."
        submit_text = "提交"
        back_text = "返回语言选择"
    else:
        title = "Malaysian Driving Law Query System"
        placeholder = "Enter your question here..."
        submit_text = "Submit"
        back_text = "Back to Language Selection"

    return render_template('chatbot.html', lang=lang, title=title, placeholder=placeholder, submit_text=submit_text, back_text=back_text)

@app.route("/graph")
def graph():
    lang = session.get("language", "en") 
    return render_template("graph.html", lang=lang)

@app.route("/get-kg-json")
def get_kg_json():
    lang = request.args.get("lang", "en")
    json_path = os.path.join(os.path.dirname(__file__), "static", "cleaned_kg_to_json.json")
    if not os.path.exists(json_path):
        return jsonify({"error": "KG JSON file not found."}), 404

    with open(json_path, "r", encoding="utf-8") as f:
        kg_data = json.load(f)

    def filter_label(label_with_lang):
        if "@ms" in label_with_lang and lang == "ms":
            return label_with_lang.replace("@ms", "")
        elif "@zh" in label_with_lang and lang == "zh":
            return label_with_lang.replace("@zh", "")
        elif "@en" in label_with_lang and lang == "en":
            return label_with_lang.replace("@en", "")
        return label_with_lang.split("@")[0] if "@" in label_with_lang else label_with_lang

    for node in kg_data["nodes"]:
        node["label"] = filter_label(node.get("label", node["id"]))

    return jsonify(kg_data)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    original_question = data.get("question", "")
    lang = data.get("lang", "ms").strip().lower()
    context = data.get("context", "")
    user_act = data.get("act", "").strip().lower().replace(" ", "_")

    if lang != "ms":
        translated = translator.translate(original_question, src=lang, dest="ms")
        question = translated.text
    else:
        question = original_question

    q_type = detect_type(question)
    section = extract_section(question)

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

    if section and q_type != "kandungan":
        kg_answer = query_kg(section, q_type)
        if kg_answer:
            return jsonify({"source": "kg", "answer": kg_answer})

    dataset_entry = None
    if act and section:
        key = f"{act}_sec_{section}"
        dataset_entry = DATASET.get(key)

    if not context.strip() and dataset_entry:
        context = dataset_entry["context"]
    elif not context.strip() and section:
        raw_context = query_kg(section, "kandungan") or ""
        context = preprocess_and_stem(raw_context)

    prompt = f"Arahan: {question} Berdasarkan konteks berikut. Konteks: {context}"
    tokens = tokenizer(prompt, max_length=512, truncation=True, return_tensors="pt")
    output = model.generate(**tokens, max_length=128)
    model_answer = tokenizer.decode(output[0], skip_special_tokens=True)

    if lang != "ms":
        back_translated = translator.translate(model_answer, src="ms", dest=lang).text
        return jsonify({"source": "model", "answer": back_translated})

    return jsonify({"source": "model", "answer": model_answer})

# Entry point
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)

