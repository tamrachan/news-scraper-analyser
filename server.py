from flask import Flask, jsonify
import subprocess
import sys
print("Python executable:", sys.executable)

app = Flask(__name__)

@app.route('/run-main')
def run_main():
    try:
        # Run your main.py script and capture output
        print("Running script")
        result = subprocess.run([sys.executable, 'server_main.py'], capture_output=True, text=True)
        output = result.stdout
        error = result.stderr

        # Always log the output for debugging
        print("STDOUT:\n", result.stdout)
        print("STDERR:\n", result.stderr)
        
        return jsonify({'output': output, 'error': error})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)