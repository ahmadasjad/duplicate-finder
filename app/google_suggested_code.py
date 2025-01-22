import os
import hashlib
import base64
from IPython.display import display, HTML
from google.colab import files
import json

def generate_file_hash(filepath):
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return None  # Indicate hash failed.

def find_duplicate_files(dir_path):
    files_info = {}  # {filepath: {name, size, ext, hash}}
    for root, _, files in os.walk(dir_path):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                file_size = os.path.getsize(filepath)
                file_name = os.path.splitext(file)[0]
                file_ext = os.path.splitext(file)[1].lower()
                file_hash = generate_file_hash(filepath)

                files_info[filepath] = {
                    'name': file_name,
                    'size': file_size,
                    'ext': file_ext,
                    'hash': file_hash
                }
            except Exception as e:
                print(f"Error processing {filepath}: {e}")

    return files_info


def group_duplicates(files_info, criteria):
    grouped = {}
    for filepath, info in files_info.items():
        key = tuple(info.get(c) for c in criteria) # create a tuple with criteria
        if None in key: # ignore if any criteria is null
          continue
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(filepath)

    return {k:v for k,v in grouped.items() if len(v) > 1} # return only duplicates


def create_file_preview(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in ('.jpg', '.jpeg', '.png', '.gif'):
            with open(filepath, 'rb') as f:
                encoded_image = base64.b64encode(f.read()).decode('utf-8')
            return f'<img src="data:image/{ext[1:]};base64,{encoded_image}" width="100px" alt="Image Preview"/>'
        elif ext in ('.mp4', '.mov', '.avi'):
          return f'<video src="{filepath}" width="100px" controls></video>'
        elif ext == '.pdf':
          return f'<embed src="{filepath}" width="100px" height="100px" type="application/pdf" />'
        elif ext in (".txt", ".csv", ".json", ".log"):
          with open(filepath, "r") as f:
              content = f.read()
          return f'<button onclick="showContent(event,\'{base64.b64encode(content.encode()).decode()}\')" >Preview Text</button>'

        else:
           return "Can't Preview"
    except Exception as e:
        return f"Error: {e}"


def create_html_table(duplicates):
    table_html = """
    <table id='duplicateTable' border='1'>
      <thead>
        <tr>
          <th>Select</th>
          <th>Preview</th>
          <th>File Path</th>
           <th>File Name</th>
          <th>File Size</th>
          <th>File Extension</th>
        </tr>
      </thead>
      <tbody>
    """
    file_index = 0
    for _, filepaths in duplicates.items():
        for filepath in filepaths:
            file_name = os.path.splitext(os.path.basename(filepath))[0]
            file_size = os.path.getsize(filepath)
            file_ext = os.path.splitext(filepath)[1].lower()
            preview_html = create_file_preview(filepath)
            table_html += f"""
                <tr data-group-id='group_{file_index}'>
                <td><input type='checkbox'  class='file-checkbox' id='file_{file_index}' data-group-id='group_{file_index}' data-file-path='{filepath}' checked></td>
                <td>{preview_html}</td>
                <td>{filepath}</td>
                <td>{file_name}</td>
                 <td>{file_size} bytes</td>
                <td>{file_ext}</td>
               </tr>
            """
            file_index += 1
    table_html += """
        </tbody>
        </table>
         <button id='deleteButton'>Delete Selected</button>
         <div id="myModal" class="modal">
            <div class="modal-content">
              <span class="close">×</span>
                <div id="modalContent"></div>
             </div>
            </div>
        """

    return table_html


def create_script(duplicates):

  return  f"""
    <style>
       .modal {{
          display: none;
          position: fixed;
          z-index: 1;
          left: 0;
          top: 0;
          width: 100%;
          height: 100%;
          overflow: auto;
          background-color: rgba(0,0,0,0.4);
        }}

       .modal-content {{
        background-color: #fefefe;
        margin: 15% auto;
        padding: 20px;
        border: 1px solid #888;
        width: 80%;
        overflow: scroll;
         height: 50%;
        }}

         .close {{
         color: #aaa;
        float: right;
         font-size: 28px;
         font-weight: bold;
         cursor: pointer;
       }}

     </style>
    <script>

      const checkboxes = document.querySelectorAll('.file-checkbox');


      checkboxes.forEach(checkbox => {{
          checkbox.addEventListener('change', function() {{
              const groupId = this.getAttribute('data-group-id');
              const groupCheckboxes = document.querySelectorAll(`input[data-group-id='${{groupId}}']`);
              const checkedInGroup = Array.from(groupCheckboxes).filter(cb => cb.checked);

            // Ensure at least one checkbox remains checked in each group
             if (checkedInGroup.length === 0) {{
                this.checked = true;
              }}
            }});
        }});

        document.getElementById('deleteButton').addEventListener('click', function() {{
           const filesToDelete = Array.from(document.querySelectorAll('.file-checkbox:checked')).map(cb => cb.getAttribute('data-file-path'));
           google.colab.kernel.invokeFunction('delete_files', [filesToDelete], {{}});

         }});


        function showContent(event, content){{
             var modal = document.getElementById("myModal");
             var modalContent = document.getElementById("modalContent");
             var closeBtn = document.getElementsByClassName("close")[0];
             modal.style.display = "block";
            modalContent.innerText = atob(content);

          closeBtn.onclick = function() {{
              modal.style.display = "none";
            }}

            window.onclick = function(event) {{
              if (event.target == modal) {{
                modal.style.display = "none";
              }}
            }}
        }}

    </script>
  """


def delete_files(files_to_delete):
    deleted_count = 0
    for filepath in files_to_delete:
      try:
        os.remove(filepath)
        deleted_count += 1
        print(f"Deleted: {filepath}")
      except Exception as e:
        print(f"Error deleting: {filepath} - {e}")

    if deleted_count == 0:
      print("No Files were deleted")
    else:
      print(f"Total {deleted_count} files deleted.")



def main(target_dir, criteria):
    files_info = find_duplicate_files(target_dir)
    duplicates = group_duplicates(files_info, criteria)

    html_table = create_html_table(duplicates)
    script = create_script(duplicates)
    display(HTML(html_table+ script))

