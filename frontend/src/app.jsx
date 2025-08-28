import React, { useState } from "react";

export default function App() {
  const [activeTab, setActiveTab] = useState("qna");
  const [repoUrl, setRepoUrl] = useState("");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [reviewResult, setReviewResult] = useState("");
  const [autoFix, setAutoFix] = useState(false);

  const handleQnASubmit = async () => {
    const res = await fetch("http://localhost:8000/qna", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl, query }),
    });
    const data = await res.json();
    setAnswer(data.answer || "No response");
  };

  const handleReview = async () => {
    const res = await fetch("http://localhost:8000/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl, auto_fix: autoFix }),
    });
    const data = await res.json();
    setReviewResult(data.result || "No issues found");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-8">
      <h1 className="text-3xl font-bold mb-6">AI Code Review & QnA Agent</h1>

      {/* Toggle Buttons */}
      <div className="flex space-x-4 mb-6">
        <button
          className={`px-6 py-2 rounded-lg shadow ${
            activeTab === "qna" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => setActiveTab("qna")}
        >
          QnA
        </button>
        <button
          className={`px-6 py-2 rounded-lg shadow ${
            activeTab === "review" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => setActiveTab("review")}
        >
          Review
        </button>
      </div>

      {/* Repo URL (shared) */}
      <div className="w-full max-w-lg mb-6">
        <input
          type="text"
          placeholder="Enter GitHub Repo URL"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          className="w-full p-3 rounded-lg border shadow"
        />
      </div>

      {/* QnA Section */}
      {activeTab === "qna" && (
        <div className="w-full max-w-lg space-y-4">
          <textarea
            placeholder="Ask a question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full p-3 rounded-lg border shadow"
          />
          <button
            onClick={handleQnASubmit}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg shadow"
          >
            Submit Query
          </button>
          {answer && (
            <div className="mt-4 p-4 bg-white rounded-lg shadow">{answer}</div>
          )}
        </div>
      )}

      {/* Review Section */}
      {activeTab === "review" && (
        <div className="w-full max-w-lg space-y-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoFix}
              onChange={(e) => setAutoFix(e.target.checked)}
            />
            <span>Enable Auto Fix</span>
          </label>
          <button
            onClick={handleReview}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg shadow"
          >
            Run Review
          </button>
          {reviewResult && (
            <div className="mt-4 p-4 bg-white rounded-lg shadow">
              {reviewResult}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
