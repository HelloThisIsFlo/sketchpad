from sketchpad.server import create_app

app = create_app()
app.run(transport="http", host="0.0.0.0", port=8000)
