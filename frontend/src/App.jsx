import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8001";

const EMPTY_PROGRESS = {
  session_id: "",
  total_attempts: 0,
  total_questions: 0,
  correct_answers: 0,
  accuracy: 0,
  topics_practiced: 0,
};

function getOrCreateSessionId() {
  const existing = localStorage.getItem("pmp_session_id");
  if (existing) return existing;

  const created = `demo-user-${Date.now()}`;
  localStorage.setItem("pmp_session_id", created);
  return created;
}

function optionKey(value) {
  const text = String(value ?? "").trim();
  const match = text.match(/^([A-Z])[\.\)\:\-]/);
  if (match) return match[1];
  return text;
}

function isCorrectOption(selectedOption, correctAnswer) {
  const selected = String(selectedOption ?? "").trim();
  const correct = String(correctAnswer ?? "").trim();
  return selected === correct || optionKey(selected) === optionKey(correct);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      data?.detail ||
      data?.message ||
      `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

function normalizeTopicGroups(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.domains)) return data.domains;
  if (Array.isArray(data?.topic_groups)) return data.topic_groups;
  return [];
}

function normalizeFlatTopics(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.topics)) return data.topics;
  if (Array.isArray(data?.flat_topics)) return data.flat_topics;
  return [];
}

export default function App() {
  const [sessionId] = useState(getOrCreateSessionId);

  const [topicGroups, setTopicGroups] = useState([]);
  const [flatTopics, setFlatTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);

  const [selectedTopicSlug, setSelectedTopicSlug] = useState("");
  const [questionInput, setQuestionInput] = useState("");
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [explanationResult, setExplanationResult] = useState(null);

  const [quizMode, setQuizMode] = useState("multi-topic");
  const [quizTopicSlug, setQuizTopicSlug] = useState("");
  const [multiTopicSlugs, setMultiTopicSlugs] = useState([]);
  const [difficulty, setDifficulty] = useState("exam");
  const [numQuestions, setNumQuestions] = useState(3);

  const [quizLoading, setQuizLoading] = useState(false);
  const [quizResponse, setQuizResponse] = useState(null);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  const [quizSaved, setQuizSaved] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  const [progress, setProgress] = useState(EMPTY_PROGRESS);
  const [progressLoading, setProgressLoading] = useState(true);

  const selectedTopic = useMemo(
    () => flatTopics.find((topic) => topic.slug === selectedTopicSlug) || null,
    [flatTopics, selectedTopicSlug]
  );

  const quizEligibleTopics = useMemo(
    () => flatTopics.filter((topic) => topic.domain !== "exam-strategy"),
    [flatTopics]
  );

  async function loadTopics() {
    try {
      setTopicsLoading(true);

      const [groupedRaw, flatRaw] = await Promise.all([
        requestJson(`${API_BASE}/api/topics`),
        requestJson(`${API_BASE}/api/topics/flat`),
      ]);

      const grouped = normalizeTopicGroups(groupedRaw);
      const flat = normalizeFlatTopics(flatRaw);

      setTopicGroups(grouped);
      setFlatTopics(flat);

      if (!selectedTopicSlug && flat.length > 0) {
        setSelectedTopicSlug(flat[0].slug);
      }

      if (!quizTopicSlug && flat.length > 0) {
        const firstEligible = flat.find(
          (topic) => topic.domain !== "exam-strategy"
        );
        if (firstEligible) setQuizTopicSlug(firstEligible.slug);
      }
    } catch (error) {
      alert(`Failed to load topics from backend.\n\n${error.message}`);
    } finally {
      setTopicsLoading(false);
    }
  }

  async function loadProgress() {
    try {
      setProgressLoading(true);

      const data = await requestJson(`${API_BASE}/api/progress/summary`, {
        headers: {
          "X-Session-Id": sessionId,
        },
      });

      setProgress({
        session_id: data?.session_id ?? sessionId,
        total_attempts: data?.total_attempts ?? 0,
        total_questions: data?.total_questions ?? 0,
        correct_answers: data?.correct_answers ?? 0,
        accuracy: data?.accuracy ?? 0,
        topics_practiced: data?.topics_practiced ?? 0,
      });
    } catch (error) {
      console.error("Progress load failed:", error);
      setProgress({
        ...EMPTY_PROGRESS,
        session_id: sessionId,
      });
    } finally {
      setProgressLoading(false);
    }
  }

  useEffect(() => {
    loadTopics();
    loadProgress();
  }, []);

  async function handleExplainTopic() {
    if (!selectedTopicSlug) {
      alert("Please select a topic first.");
      return;
    }

    if (!questionInput.trim()) {
      alert("Please enter a question.");
      return;
    }

    try {
      setExplanationLoading(true);
      setExplanationResult(null);

      const data = await requestJson(`${API_BASE}/api/chat/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          topic_slug: selectedTopicSlug,
          question: questionInput.trim(),
        }),
      });

      setExplanationResult(data);
    } catch (error) {
      alert(`Failed to explain topic.\n\n${error.message}`);
    } finally {
      setExplanationLoading(false);
    }
  }

  function buildQuizPayload() {
    if (quizMode === "single-topic") {
      if (!quizTopicSlug) {
        throw new Error("Please select a quiz topic.");
      }

      return {
        quiz_mode: "single-topic",
        topic_slug: quizTopicSlug,
        difficulty,
        num_questions: Number(numQuestions),
      };
    }

    if (quizMode === "multi-topic") {
      if (multiTopicSlugs.length === 0) {
        throw new Error("Please select at least one topic.");
      }

      return {
        quiz_mode: "multi-topic",
        topic_slugs: multiTopicSlugs,
        difficulty,
        num_questions: Number(numQuestions),
      };
    }

    return {
      quiz_mode: "mock-test",
      difficulty,
      num_questions: Number(numQuestions),
    };
  }

  async function handleGenerateQuiz() {
    try {
      setQuizLoading(true);
      setQuizResponse(null);
      setSelectedAnswers({});
      setQuizSaved(false);
      setSaveMessage("");

      const payload = buildQuizPayload();

      const data = await requestJson(`${API_BASE}/api/quiz/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify(payload),
      });

      setQuizResponse(data);
    } catch (error) {
      alert(`Failed to generate quiz.\n\n${error.message}`);
    } finally {
      setQuizLoading(false);
    }
  }

  async function saveQuizAttempt(finalSelections, quizData) {
    if (!quizData || !Array.isArray(quizData.questions) || quizSaved) return;

    const totalQuestions = quizData.questions.length;

    const correctAnswers = quizData.questions.reduce((count, question, index) => {
      const selected = finalSelections[index];
      if (!selected) return count;
      return count + (isCorrectOption(selected, question.correct_answer) ? 1 : 0);
    }, 0);

    const topicSlugs =
      quizData.topic_slugs && Array.isArray(quizData.topic_slugs)
        ? quizData.topic_slugs
        : quizData.topic_slug
        ? [quizData.topic_slug]
        : quizMode === "multi-topic"
        ? multiTopicSlugs
        : quizMode === "single-topic" && quizTopicSlug
        ? [quizTopicSlug]
        : [];

    try {
      await requestJson(`${API_BASE}/api/progress/quiz-attempt`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId,
        },
        body: JSON.stringify({
          quiz_mode: quizData.quiz_mode || quizMode,
          difficulty: quizData.difficulty || difficulty,
          topic_slugs: topicSlugs,
          total_questions: totalQuestions,
          correct_answers: correctAnswers,
        }),
      });

      setQuizSaved(true);
      setSaveMessage("Quiz attempt saved and progress report refreshed.");
      await loadProgress();
    } catch (error) {
      setSaveMessage(`Quiz generated, but saving progress failed: ${error.message}`);
    }
  }

  async function handleSelectAnswer(questionIndex, option) {
    if (!quizResponse?.questions?.[questionIndex]) return;
    if (selectedAnswers[questionIndex]) return;

    const updatedSelections = {
      ...selectedAnswers,
      [questionIndex]: option,
    };

    setSelectedAnswers(updatedSelections);

    const totalQuestions = quizResponse.questions.length;
    const answeredCount = Object.keys(updatedSelections).length;

    if (answeredCount === totalQuestions && !quizSaved) {
      await saveQuizAttempt(updatedSelections, quizResponse);
    }
  }

  function toggleMultiTopic(slug) {
    setMultiTopicSlugs((current) =>
      current.includes(slug)
        ? current.filter((item) => item !== slug)
        : [...current, slug]
    );
  }

  function renderQuizQuestion(question, index) {
    const selected = selectedAnswers[index];
    const answered = Boolean(selected);

    return (
      <div key={`${question.question}-${index}`} className="quiz-card">
        <div className="quiz-question">
          {index + 1}. {question.question}
        </div>

        <div className="quiz-options">
          {question.options.map((option) => {
            const picked = selected === option;
            const correct = isCorrectOption(option, question.correct_answer);

            let className = "quiz-option";
            if (answered) {
              if (picked && correct) className += " correct";
              else if (picked && !correct) className += " incorrect";
              else if (correct) className += " correct-outline";
            }

            return (
              <button
                key={option}
                type="button"
                className={className}
                onClick={() => handleSelectAnswer(index, option)}
                disabled={answered}
              >
                {option}
              </button>
            );
          })}
        </div>

        {answered && (
          <div className="quiz-feedback">
            <div
              className={
                isCorrectOption(selected, question.correct_answer)
                  ? "feedback-correct"
                  : "feedback-wrong"
              }
            >
              {isCorrectOption(selected, question.correct_answer)
                ? "✅ Correct"
                : "❌ Incorrect"}
            </div>

            <div className="quiz-answer-line">
              <strong>Correct Answer:</strong> {question.correct_answer}
            </div>

            <div className="quiz-answer-line">
              <strong>Explanation:</strong> {question.explanation}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="app-container">
        <div className="hero-badge">PMP Exam Prep Assistant</div>
        <h1 className="page-title">PMP Prep Bot</h1>
        <p className="page-subtitle">
          Learn PMP topics faster with AI explanations, interactive quiz practice, and
          progress tracking.
        </p>

        <section className="section-card">
          <h2>1. Choose a Topic</h2>

          <select
            className="input-control"
            value={selectedTopicSlug}
            onChange={(e) => setSelectedTopicSlug(e.target.value)}
            disabled={topicsLoading}
          >
            <option value="">
              {topicsLoading ? "Loading topics..." : "Select a topic"}
            </option>
            {flatTopics.map((topic) => (
              <option key={topic.slug} value={topic.slug}>
                {topic.name}
              </option>
            ))}
          </select>

          <div className="topics-area">
            <h3>Available Topics</h3>
            {topicGroups.map((group) => (
              <div key={group.domain} className="topic-group-card">
                <div className="topic-group-title">{group.domain_label}</div>
                <ul>
                  {group.topics.map((topic) => (
                    <li key={topic.slug}>{topic.name}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {selectedTopic && (
            <div className="selected-topic-card">
              <div className="selected-topic-label">Selected Topic</div>
              <div className="selected-topic-title">{selectedTopic.name}</div>
              <div className="selected-topic-description">
                {selectedTopic.description}
              </div>
              <div className="selected-topic-keywords">
                <strong>Keywords:</strong> {selectedTopic.keywords.join(", ")}
              </div>
            </div>
          )}
        </section>

        <div className="two-column-grid">
          <section className="section-card">
            <h2>2. Ask for an Explanation</h2>

            <textarea
              className="textarea-control"
              rows={5}
              value={questionInput}
              onChange={(e) => setQuestionInput(e.target.value)}
              placeholder="Ask something like: Explain qualitative and quantitative risk analysis for PMP exam preparation."
            />

            <button
              className="primary-button"
              onClick={handleExplainTopic}
              disabled={explanationLoading}
            >
              {explanationLoading ? "Explaining..." : "Explain Topic"}
            </button>

            {explanationResult && (
              <div className="result-card">
                <h3>AI Explanation</h3>
                <div className="result-text">{explanationResult.answer}</div>
              </div>
            )}
          </section>

          <section className="section-card">
            <h2>3. Generate Quiz</h2>

            <label className="field-label">Quiz Mode</label>
            <select
              className="input-control"
              value={quizMode}
              onChange={(e) => {
                setQuizMode(e.target.value);
                setQuizResponse(null);
                setSelectedAnswers({});
                setQuizSaved(false);
                setSaveMessage("");
              }}
            >
              <option value="single-topic">Single Topic</option>
              <option value="multi-topic">Multi Topic</option>
              <option value="mock-test">Mock Test</option>
            </select>

            {quizMode === "single-topic" && (
              <>
                <label className="field-label">Quiz Topic</label>
                <select
                  className="input-control"
                  value={quizTopicSlug}
                  onChange={(e) => setQuizTopicSlug(e.target.value)}
                >
                  <option value="">Select quiz topic</option>
                  {quizEligibleTopics.map((topic) => (
                    <option key={topic.slug} value={topic.slug}>
                      {topic.name}
                    </option>
                  ))}
                </select>
              </>
            )}

            {quizMode === "multi-topic" && (
              <>
                <label className="field-label">Select Multiple Topics</label>
                <div className="checkbox-panel">
                  {quizEligibleTopics.map((topic) => (
                    <label key={topic.slug} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={multiTopicSlugs.includes(topic.slug)}
                        onChange={() => toggleMultiTopic(topic.slug)}
                      />
                      <span>{topic.name}</span>
                    </label>
                  ))}
                </div>
              </>
            )}

            {quizMode === "mock-test" && (
              <div className="info-box">
                Mock Test mode will generate questions randomly from all quiz-eligible topics.
              </div>
            )}

            <label className="field-label">Difficulty</label>
            <select
              className="input-control"
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="exam">Exam</option>
            </select>

            <label className="field-label">Number of Questions</label>
            <select
              className="input-control"
              value={numQuestions}
              onChange={(e) => setNumQuestions(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((count) => (
                <option key={count} value={count}>
                  {count}
                </option>
              ))}
            </select>

            <div className="small-note">
              You can generate between 1 and 10 questions.
            </div>

            <button
              className="primary-button"
              onClick={handleGenerateQuiz}
              disabled={quizLoading}
            >
              {quizLoading ? "Generating..." : "Generate Quiz"}
            </button>

            {saveMessage && <div className="save-message">{saveMessage}</div>}

            {quizResponse?.questions?.length > 0 && (
              <div className="result-card">
                <h3>Quiz Questions</h3>
                {quizResponse.questions.map((question, index) =>
                  renderQuizQuestion(question, index)
                )}
              </div>
            )}
          </section>
        </div>

        <section className="section-card">
          <h2>4. Progress Report</h2>

          {progressLoading ? (
            <div className="small-note">Loading progress...</div>
          ) : (
            <div className="progress-grid">
              <div className="metric-card">
                <div className="metric-label">Session ID</div>
                <div className="metric-value">{progress.session_id || sessionId}</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Total Attempts</div>
                <div className="metric-value">{progress.total_attempts}</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Total Questions</div>
                <div className="metric-value">{progress.total_questions}</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Correct Answers</div>
                <div className="metric-value">{progress.correct_answers}</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Accuracy</div>
                <div className="metric-value">{progress.accuracy}%</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Topics Practiced</div>
                <div className="metric-value">{progress.topics_practiced}</div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}