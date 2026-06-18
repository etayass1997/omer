import json
import os
import re

import anthropic
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "אתה עומר, סוכן תמחור ישראלי חכם. תמיד חפש מחירים בזאפ.co.il ובאתרים ישראליים קודם. "
    "תן מחירים בשקלים. היה ישיר וממוקד. אם אינך בטוח במחיר - אמור זאת. "
    "תסביר תמיד מה משפיע על המחיר."
)

SEARCH_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 4},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 4, "max_content_tokens": 4000},
]


def api_error_response(e):
    if isinstance(e, anthropic.RateLimitError):
        return jsonify({"error": "יותר מדי בקשות כרגע, נסה שוב בעוד דקה"}), 429
    return jsonify({"error": str(e)}), 502


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def extract_text(content_blocks):
    parts = []
    for block in content_blocks:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)


def extract_json(text):
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def run_with_tools(client, messages, max_rounds=6):
    """Run a Claude request, automatically continuing past pause_turn
    (server-side tool iteration limit) until a final text response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=SEARCH_TOOLS,
        messages=messages,
    )
    rounds = 0
    while response.stop_reason == "pause_turn" and rounds < max_rounds:
        messages = messages + [{"role": "assistant", "content": response.content}]
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=SEARCH_TOOLS,
            messages=messages,
        )
        rounds += 1
    return response


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/clarify", methods=["POST"])
def clarify():
    client = get_client()
    if not client:
        return jsonify({"error": "מפתח API לא מוגדר בשרת"}), 500

    data = request.json or {}
    product = (data.get("product") or "").strip()
    if not product:
        return jsonify({"error": "חסר שם מוצר"}), 400

    prompt = (
        f'המוצר שהמשתמש מחפש: "{product}".\n'
        "בדוק אם המוצר הזה מגיע במגוון איכויות/דגמים/מידות שמשפיעות באופן ניכר על המחיר "
        "(לדוגמה: איכות בסיסי/בינוני/פרמיום, מידה, משקל, נפח אחסון, גודל מסך וכו').\n"
        "אם כן - הכן עד 3 שאלות בירור קצרות וממוקדות בעברית שיעזרו לצמצם את החיפוש.\n"
        "אם המוצר ספציפי ופשוט מספיק (לדוגמה דגם מוצר מדויק) - אין צורך בשאלות.\n"
        "החזר רק אובייקט JSON תקין, בלי שום טקסט נוסף, בפורמט: "
        '{"needs_clarification": true/false, "questions": ["שאלה 1", "שאלה 2"]}'
    )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        return api_error_response(e)

    text = extract_text(response.content)
    parsed = extract_json(text)

    if not parsed or not parsed.get("needs_clarification"):
        return jsonify({"status": "ready"})

    questions = [q for q in parsed.get("questions", []) if q][:3]
    if not questions:
        return jsonify({"status": "ready"})

    return jsonify({"status": "questions", "questions": questions})


@app.route("/search", methods=["POST"])
def search():
    client = get_client()
    if not client:
        return jsonify({"error": "מפתח API לא מוגדר בשרת"}), 500

    data = request.json or {}
    product = (data.get("product") or "").strip()
    answers = data.get("answers") or {}
    if not product:
        return jsonify({"error": "חסר שם מוצר"}), 400

    details = ""
    if answers:
        details = "\nפרטים נוספים שסיפק המשתמש:\n" + "\n".join(
            f"- {q}: {a}" for q, a in answers.items() if a
        )

    prompt = (
        f'חפש את המחיר הטוב ביותר עבור המוצר: "{product}".{details}\n\n'
        "חפש בזאפ (zap.co.il) ובגוגל שופינג (Google Shopping), ובדפי מוצר ישראליים רלוונטיים. "
        "השווה לפחות 2-3 מקורות שונים.\n\n"
        "כשתסיים, החזר תשובה סופית שהיא אך ורק אובייקט JSON תקין (בלי טקסט נוסף, בלי ```), "
        "במבנה המדויק הזה:\n"
        "{\n"
        '  "market_summary": {"min_price": <number>, "max_price": <number>, "avg_price": <number>, "currency": "₪"},\n'
        '  "cheapest": [\n'
        '    {"rank": 1, "site": "<שם האתר>", "price": <number>, "url": "<קישור לדף המוצר>"},\n'
        '    {"rank": 2, "site": "<שם האתר>", "price": <number>, "url": "<קישור לדף המוצר>"}\n'
        "  ],\n"
        '  "tip": "<טיפ קצר של עומר על מה לשים לב לפני הקנייה>"\n'
        "}\n"
        "אם לא מצאת מספיק נתונים, מלא הערכה סבירה והסבר זאת בתוך ה-tip."
    )

    messages = [{"role": "user", "content": prompt}]

    try:
        response = run_with_tools(client, messages)
    except anthropic.APIError as e:
        return api_error_response(e)

    if response.stop_reason == "refusal":
        return jsonify({"error": "עומר לא הצליח לבצע את החיפוש הזה"}), 422

    text = extract_text(response.content)
    parsed = extract_json(text)

    if not parsed:
        return jsonify({"error": "לא הצלחתי לפענח את תוצאות החיפוש", "raw": text}), 502

    return jsonify({"status": "ok", "result": parsed})


@app.route("/chat", methods=["POST"])
def chat():
    client = get_client()
    if not client:
        return jsonify({"error": "מפתח API לא מוגדר בשרת"}), 500

    data = request.json or {}
    product = (data.get("product") or "").strip()
    result = data.get("result")
    history = data.get("history") or []
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "חסרה הודעה"}), 400

    context = f'המוצר שעליו מדובר: "{product}".\n'
    if result:
        context += f"תוצאות חיפוש קודמות: {json.dumps(result, ensure_ascii=False)}\n"

    messages = [{"role": "user", "content": context.strip()}, {"role": "assistant", "content": "הבנתי, אני כאן לעזור עם שאלות המשך."}]
    for turn in history:
        role = turn.get("role")
        text = turn.get("text", "")
        if role in ("user", "assistant") and text:
            messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": message})

    try:
        response = run_with_tools(client, messages)
    except anthropic.APIError as e:
        return api_error_response(e)

    if response.stop_reason == "refusal":
        return jsonify({"error": "עומר לא הצליח לענות על זה"}), 422

    reply = extract_text(response.content)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
