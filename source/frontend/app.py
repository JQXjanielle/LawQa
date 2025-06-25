import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
import requests


app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

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

    return render_template('chatbot.html',
        lang=lang,
        title=title,
        placeholder=placeholder,
        submit_text=submit_text,
        back_text=back_text
    )

@app.route("/graph")
def graph():
    lang = session.get("language", "en") 
    return render_template("graph.html", lang=lang)

@app.route("/get-kg-json")
def get_kg_json():
    lang = request.args.get("lang", "en")
    json_path = os.path.join(os.path.dirname(__file__), "static", "cleaned_kg_to_json.json")

    print("DEBUG: Loading cleaned KG JSON from:", json_path)

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

    # Apply language filter to labels
    for node in kg_data["nodes"]:
        node["label"] = filter_label(node.get("label", node["id"]))

    return jsonify(kg_data)

@app.route("/ask-question", methods=["POST"])
def ask_question():
    question = request.json.get("question", "")
    context = request.json.get("context", "")
    lang = session.get("language", "ms")
    act = request.json.get("act", "")  # ✅ NEW

    try:
        # Forward to backend Flask API
        response = requests.post(
            "http://localhost:5001/ask",
            json={"question": question, "context": context, "lang": lang, "act": act}  # ✅ NEW
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
