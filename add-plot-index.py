import os

# Directory containing your PNG files
directory = "plots"

# HTML file to index the images
index_html_path = os.path.join(directory, "index.html")

# Extract year from filenames and sort
files = [f for f in os.listdir(directory) if f.endswith(".png")]
files.sort(key=lambda x: int(x.split('.')[0]))  # Assuming filename format is "year.png"

# Start the HTML file
with open(index_html_path, "w") as index_file:
    index_file.write("""
<html>
<head>
<title>Yearly Data Visualization</title>
<style>
body { font-family: Arial, sans-serif; padding: 20px; }
.grid-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
.grid-item { padding: 10px; background-color: #f0f0f0; border: 1px solid #ddd; }
.grid-item img { width: 100%; height: auto; cursor: pointer; }
#modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgb(0,0,0,0.9); }
.modal-content { margin: 10% auto; display: block; width: 80%; max-width: 700px; }
.close { position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }
</style>
<script>
function enlargeImage(src) {
    document.getElementById("img01").src = src;
    document.getElementById("modal").style.display = "block";
}
function closeModal() {
    document.getElementById("modal").style.display = "none";
}
</script>
</head>
<body>

<h1>Yearly Data Visualization</h1>
<p>Below is the data visualized for each year. Click on an image to enlarge it.</p>
<div class="grid-container">
""")

    for filename in files:
        year = filename.split('.')[0]
        index_file.write(f'<div class="grid-item"><strong>{year}</strong><br><img src="{filename}" alt="Data for {year}" onclick="enlargeImage(this.src)"></div>\n')

    index_file.write("""
</div>

<!-- The Modal -->
<div id="modal" onclick="closeModal()">
  <span class="close">&times;</span>
  <img class="modal-content" id="img01">
</div>

</body>
</html>
""")

print("Index generated successfully.")
