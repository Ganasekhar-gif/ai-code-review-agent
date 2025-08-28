import React, { useState } from "react";

export default function App() {
  const [activeTab, setActiveTab] = useState("qna");
  const [repoUrl, setRepoUrl] = useState("");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [reviewResult, setReviewResult] = useState("");
  const [autoFix, setAutoFix] = useState(false);

  // Loading states
  const [loadingQna, setLoadingQna] = useState(false);
  const [loadingReview, setLoadingReview] = useState(false);

  // -----------------------------
  // Handlers
  // -----------------------------
  const handleQnASubmit = async () => {
    if (!query.trim()) return;
    setLoadingQna(true);
    setAnswer("");

    try {
      const res = await fetch("http://localhost:8000/qna", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, query }),
      });

      const data = await res.json();
      const shownQuery = data.query || query;
      const shownAnswer = data.answer || "No response";
      setAnswer(`${shownQuery}\n\n${shownAnswer}`);
    } catch (err) {
      setAnswer("❌ Error fetching answer");
    } finally {
      setLoadingQna(false);
      setQuery("");
    }
  };

  const handleReview = async () => {
    setLoadingReview(true);
    setReviewResult("");

    try {
      const res = await fetch("http://localhost:8000/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl, auto_fix: autoFix }),
      });

      const data = await res.json();
      setReviewResult(
        data.formatted || "No issues found"
      );
    } catch (err) {
      setReviewResult("❌ Error running review");
    } finally {
      setLoadingReview(false);
    }
  };

  const handleReset = async () => {
    if (!repoUrl) {
      alert("Please enter a repo URL before resetting.");
      return;
    }

    await fetch("http://localhost:8000/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl }),
    });

    alert("ChromaDB collection reset ✅");
  };

  // -----------------------------
  // Spinner Component
  // -----------------------------
  const Spinner = () => (
    <div className="flex justify-center items-center">
      <div className="w-6 h-6 border-4 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
    </div>
  );

  // -----------------------------
  // UI
  // -----------------------------
  return (
    <div className="min-h-screen grid grid-cols-[280px_1fr] bg-gradient-to-br from-gray-900 via-black to-gray-800 text-white">
      {/* Sidebar */}
      <aside className="bg-black/40 backdrop-blur-md border-r border-indigo-700/40 p-6 flex flex-col space-y-8">
        <h1 className="text-3xl font-extrabold text-indigo-400 tracking-wider">
          🚀 AI Agent
        </h1>

        <nav className="flex flex-col space-y-4">
          <button
            onClick={() => setActiveTab("qna")}
            className={`px-5 py-4 rounded-xl text-left font-bold transition-all ${
              activeTab === "qna"
                ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-700/50"
                : "hover:bg-gray-800/60 text-gray-300"
            }`}
          >
            ❓ QnA
          </button>

          <button
            onClick={() => setActiveTab("review")}
            className={`px-5 py-4 rounded-xl text-left font-bold transition-all ${
              activeTab === "review"
                ? "bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-700/50"
                : "hover:bg-gray-800/60 text-gray-300"
            }`}
          >
            🛠 Review
          </button>

          <button
            onClick={handleReset}
            className="px-5 py-4 rounded-xl text-left font-bold bg-gradient-to-r from-red-600 to-pink-600 text-white shadow-lg shadow-red-800/50 hover:from-red-700 hover:to-pink-700 transition"
          >
            🔄 Reset DB
          </button>
        </nav>
      </aside>

      {/* Main content */}
      <main className="p-12 flex flex-col items-center">
        <div className="w-full max-w-3xl space-y-8">
          <h2 className="text-5xl font-extrabold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-blue-400 text-center">
            AI Code Review & QnA Agent
          </h2>

          {/* Repo Input */}
          <div>
            <input
              type="text"
              placeholder="🔗 Enter GitHub Repo URL"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="w-full p-3 text-lg rounded-2xl border border-indigo-600 bg-black/40 backdrop-blur-md focus:ring-4 focus:ring-indigo-500 outline-none placeholder-gray-400"
            />
          </div>

          {/* QnA Section */}
          {activeTab === "qna" && (
            <div className="bg-black/40 backdrop-blur-lg p-6 rounded-3xl shadow-xl border border-indigo-700/40 space-y-6">
              <textarea
                placeholder="💡 Ask a question about your repo..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleQnASubmit();
                  }
                }}
                className="w-full h-24 mx-auto block p-3 text-lg rounded-2xl border border-indigo-600 bg-black/40 backdrop-blur-md focus:ring-4 focus:ring-indigo-500 outline-none resize-none placeholder-gray-400"
              />
              {loadingQna && (
                <div className="mt-4 flex justify-center items-center space-x-3">
                  <Spinner />
                  <span className="text-indigo-400 font-semibold">
                    Answering your query...
                  </span>
                </div>
              )}
              {answer && !loadingQna && (
                <div className="mt-4 p-6 bg-black/50 backdrop-blur-lg rounded-2xl border border-indigo-600 shadow text-lg whitespace-pre-wrap">
                  {answer}
                </div>
              )}
            </div>
          )}

          {/* Review Section */}
          {activeTab === "review" && (
            <div className="bg-black/40 backdrop-blur-lg p-8 rounded-3xl shadow-xl border border-indigo-700/40 space-y-6">
              <label className="flex items-center space-x-3 text-xl">
                <input
                  type="checkbox"
                  checked={autoFix}
                  onChange={(e) => setAutoFix(e.target.checked)}
                  className="w-6 h-6 accent-indigo-500"
                />
                <span>Enable Auto Fix</span>
              </label>

              <button
                onClick={handleReview}
                disabled={loadingReview}
                className="w-full py-4 text-lg font-bold bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-2xl shadow-lg shadow-indigo-800/50 hover:from-indigo-700 hover:to-blue-700 transition disabled:opacity-50"
              >
                {loadingReview ? "⏳ Running Review..." : "🛠 Run Review"}
              </button>

              {loadingReview && (
                <div className="flex justify-center items-center space-x-3">
                  <Spinner />
                  <span className="text-indigo-400 font-semibold">
                    Analyzing code...
                  </span>
                </div>
              )}

              {reviewResult && !loadingReview && (
                <div className="mt-4 p-6 bg-black/50 backdrop-blur-lg rounded-2xl border border-indigo-600 shadow text-lg overflow-auto whitespace-pre-wrap">
                  {reviewResult}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
