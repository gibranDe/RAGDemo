from flask import Flask, render_template, request, jsonify
from rag_answer import search_rag
from core.database import db_manager

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    before_str = after_str = rag_answer = ""
    performance_metrics = None
    top_k = 10
    query = ""
    ann_limit = 100

    if request.method == "POST":
        query = request.form.get("query")
        top_k = int(request.form.get("top_k"))
        rag_answer, before_str, after_str, performance_metrics = search_rag(query, context_k=top_k, ann_k=ann_limit)

    return render_template("index.html",
                           before=before_str,
                           after=after_str,
                           answer=rag_answer,
                           query=query,
                           top_k=top_k,
                           ann_limit=ann_limit,
                           performance_metrics=performance_metrics)

@app.route("/stats")
def stats():
    return jsonify(db_manager.get_collection_stats())

@app.route("/health")
def health():
    try:
        stats = db_manager.get_collection_stats()
        return jsonify({
            "status": "healthy",
            "database_connected": True,
            "collection_stats": stats
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True)