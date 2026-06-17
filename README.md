# עומר - סוכן תמחור חכם

PWA שמוצא את המחיר הכי טוב למוצר שאתה מחפש, באמצעות Claude (עם יכולת חיפוש באינטרנט).

## סטאק

- **Frontend**: `static/index.html` - קובץ אחד, HTML+CSS+JS, RTL עברית, PWA מלא
- **Backend**: `app.py` - Flask
- **AI**: Claude API (`claude-sonnet-4-6`) עם web search + web fetch

## הרצה מקומית

```bash
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...   # Windows (cmd)
# $env:ANTHROPIC_API_KEY="sk-ant-..."  # PowerShell
python app.py
```
האפליקציה תרוץ על `http://localhost:5000`.

## דפלוי ל-Render

1. **העלאה ל-GitHub** - צור ריפו חדש והעלה את כל התיקייה הזו:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - עומר"
   git remote add origin <כתובת הריפו שלך>
   git push -u origin main
   ```

2. **חיבור ל-Render**:
   - היכנס ל-[render.com](https://render.com) → New → Web Service
   - חבר את הריפו מ-GitHub
   - Render יזהה אוטומטית את `render.yaml` ויגדיר הכל

3. **הוספת `ANTHROPIC_API_KEY` כ-Environment Variable**:
   - בלוח הבקרה של השירות ב-Render → Environment
   - הוסף `ANTHROPIC_API_KEY` עם המפתח שלך מ-[console.anthropic.com](https://console.anthropic.com)
   - שמור - Render יבצע דפלוי מחדש אוטומטית

4. **עדכון `API_URL`**:
   - לאחר שהדפלוי מצליח, Render ייתן לך כתובת כמו `https://omer-pricing-agent.onrender.com`
   - מכיוון שה-frontend וה-backend רצים מאותו שירות, אפשר להשאיר את `static/config.js` עם `API_URL = ""` (ריק) - זה אומר "אותו דומיין"
   - אם בעתיד תרצה להגיש את ה-frontend ממקום אחר (למשל GitHub Pages), עדכן את `API_URL` בקובץ `static/config.js` לכתובת המלאה של ה-backend ב-Render

## נקודות קצה (API)

| Endpoint    | Method | תיאור |
|-------------|--------|-------|
| `/clarify`  | POST   | מקבל `{product}`, מחזיר שאלות בירור או `{"status": "ready"}` |
| `/search`   | POST   | מקבל `{product, answers}`, מריץ חיפוש מחירים, מחזיר תוצאות JSON |
| `/chat`     | POST   | מקבל `{product, result, history, message}`, מחזיר תשובת המשך |
