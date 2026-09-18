# LONDONBEACON

A touristic Streamlit app for discovering London attractions and getting
simple walking directions to them.

## Project structure

```
londonbeacon/
  app.py                        # the whole app (heavily commented)
  data/london_attractions.csv   # 100 attractions, 10 per category
  assets/london_3d_bg.png       # hero background image
  requirements.txt              # Python packages the app needs
  .streamlit/config.toml        # optional dark theme defaults
```

## How to run it (first time setup)

Open a terminal **inside the `londonbeacon` folder** and run:

```bash
# 1. Create an isolated Python environment just for this project
python3 -m venv .venv

# 2. Activate it (do this every time you open a new terminal)
source .venv/bin/activate          # Mac/Linux
# .venv\Scripts\activate           # Windows

# 3. Install the required packages into that environment
pip install -r requirements.txt

# 4. Run the app - this opens it in your browser automatically
streamlit run app.py
```

If VS Code shows "Import could not be resolved" warnings, it usually
means VS Code is pointed at a different Python interpreter than the
one in `.venv`. Fix it with `Cmd+Shift+P` -> "Python: Select Interpreter"
-> choose the one inside `.venv`.

## Notes on the optional GPS button

The "Use My Current Location" button uses the browser's own GPS feature
(the Geolocation API). Browsers only allow this on secure pages, so it
works on `http://localhost:8501` while testing, and will keep working
once you deploy the app to Streamlit Community Cloud (which serves
pages over `https://`).
