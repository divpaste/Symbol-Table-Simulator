from flask import Flask, render_template, request, jsonify
from source_parser import SourceParser

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/compile", methods=["POST"])
def compile_code():
    data = request.get_json() or {}
    source_code = data.get("code", "")

    parser = SourceParser()
    symbol_table, errors = parser.parse(source_code)

    scopes_data = []
    for sc in symbol_table.all_scopes:
        parent_id = sc.parent.scope_id if sc.parent else None
        
        buckets_list = []
        for b_idx, bucket in enumerate(sc.hash_table.buckets):
            chain = []
            for sym in bucket:
                chain.append({
                    "name": sym.name,
                    "data_type": sym.data_type,
                    "value": sym.value,
                    "line_number": sym.line_number,
                    "scope_id": sym.scope_id
                })
            buckets_list.append({
                "index": b_idx,
                "chain": chain
            })

        scopes_data.append({
            "scope_id": sc.scope_id,
            "scope_name": sc.scope_name,
            "parent_id": parent_id,
            "buckets": buckets_list
        })

    return jsonify({
        "scopes": scopes_data,
        "errors": errors
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)