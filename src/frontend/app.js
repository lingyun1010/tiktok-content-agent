function setText(id, value) {
  const element = document.getElementById(id);

  if (element && value !== null && value !== undefined) {
    element.textContent = String(value);
  }
}

function formatCompact(value) {
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatPercent(value) {
  return value === null || value === undefined
    ? "N/A"
    : `${(value * 100).toFixed(2)}%`;
}

function formatProvider(plan) {
  const names = {
    manual: "Manual",
    openai: "OpenAI",
    claude: "Claude",
  };
  const provider = names[plan.provider] || plan.provider;
  return `${provider} · ${plan.llm_called ? "LLM called" : "offline"}`;
}

function providerPipelineLabel(plan) {
  const provider = formatProvider(plan).split(" · ")[0];
  return `${provider} provider · ${plan.llm_called ? "LLM called" : "offline"}`;
}

function formatSource(source) {
  return source === "airtable" ? "Airtable" : "CSV";
}

function formatPostCount(count) {
  return `${count} ${count === 1 ? "post" : "posts"}`;
}

function formatIds(ids) {
  return ids.length ? ids.join(" · ") : "None";
}

let latestDashboardData = null;

function renderAnalystAnswer(answer) {
  setText("answer-summary", answer.summary);
  setText("answer-recommendation", answer.recommendation);
  setText("answer-next-action", answer.suggested_next_action);
  replaceList(
    "answer-evidence",
    answer.evidence.map(
      (item) => `${item.post_id}: ${item.metric} ${item.value}`,
    ),
    "li",
  );
  replaceList("answer-limitations", answer.limitations || [], "li");
  setText(
    "analyst-mode",
    `${answer.provider || "manual"} analyst · ${
      answer.llm_called ? "LLM called" : "offline"
    }`,
  );
  renderAnalystTrace(answer.trace);
}

function renderAnalystTrace(trace) {
  const traceSection = document.getElementById("answer-trace");

  if (!traceSection) {
    return;
  }

  if (!trace) {
    traceSection.setAttribute("hidden", "");
    setText("trace-intent", "");
    replaceList("trace-tools", [], "li");
    replaceList("trace-observations", [], "li");
    replaceList("trace-limitations", [], "li");
    return;
  }

  traceSection.removeAttribute("hidden");
  setText("trace-intent", trace.interpreted_intent || "Unavailable");
  replaceList("trace-tools", trace.tools_used || [], "li");
  replaceList("trace-observations", trace.observations || [], "li");
  replaceList("trace-limitations", trace.limitations || [], "li");
}

function replaceList(id, items, itemName) {
  const list = document.getElementById(id);

  if (!list) {
    return;
  }

  list.replaceChildren(
    ...items.map((item) => {
      const element = document.createElement(itemName);
      element.textContent = item;
      return element;
    }),
  );
}

function buildPostRows(posts) {
  const tableBody = document.getElementById("post-summary-rows");

  if (!tableBody) {
    return;
  }

  tableBody.replaceChildren(
    ...posts.map((post) => {
      const row = document.createElement("tr");
      const values = [
        post.post_id,
        post.format,
        post.topic || "Unavailable",
        formatCompact(post.views),
        formatPercent(post.engagement_rate),
        formatPercent(post.average_watch_ratio),
      ];

      values.forEach((value, index) => {
        const cell = document.createElement("td");
        cell.textContent = value;

        if (index >= 3) {
          cell.classList.add("numeric");
        }

        row.append(cell);
      });

      const signalCell = document.createElement("td");
      const signals = post.signals.length ? post.signals : ["none"];

      signals.forEach((signal) => {
        const tag = document.createElement("span");
        tag.className = "table-signal";
        tag.textContent = signal.replaceAll("_", " ");
        signalCell.append(tag);
      });

      row.append(signalCell);
      return row;
    }),
  );
}

function validateDashboardData(data) {
  return Boolean(
    data &&
      data.generated_at &&
      data.source &&
      data.provider &&
      data.dataset_overview &&
      Array.isArray(data.posts) &&
      data.metrics_summary &&
      data.content_plan &&
      data.script &&
      Array.isArray(data.hashtags),
  );
}

function renderDashboard(data) {
  latestDashboardData = data;

  const {
    generated_at: generatedAt,
    source,
    dataset_overview: summary,
    posts,
    signals,
    content_plan: plan,
  } = data;
  const item = plan.content_item;
  const strategy = plan.strategy;
  const topPost = summary.top_post;
  const sourceName = formatSource(source);
  const providerLabel = formatProvider(plan);

  setText("dashboard-mode", `${sourceName} · latest pipeline run`);
  setText(
    "dashboard-intro",
    `A human-readable view of the latest ${sourceName} metrics, content signals, and reviewable ${plan.provider} draft.`,
  );
  setText("pipeline-source", `${sourceName} ingested`);
  setText("pipeline-source-detail", formatPostCount(summary.post_count));
  setText("pipeline-provider", providerPipelineLabel(plan));
  setText("dataset-title", `Latest ${sourceName} data at a glance`);
  setText("signals-title", `What the ${sourceName} data is telling us`);
  setText("metric-post-count", summary.post_count);
  setText("metric-post-detail", `${sourceName} source records`);
  setText("metric-total-views", formatCompact(summary.total_views));
  setText(
    "metric-average-views",
    `${formatCompact(summary.average_views)} average per post`,
  );
  setText("metric-engagement", formatPercent(summary.average_engagement_rate));
  setText("metric-watch", formatPercent(summary.average_watch_ratio));
  setText(
    "generated-at",
    `Generated ${new Date(generatedAt).toLocaleString()}`,
  );

  setText("top-post-hook", `“${topPost.hook || "Hook unavailable"}”`);
  setText(
    "top-post-meta",
    `${topPost.format} · ${topPost.topic || "Topic unavailable"} · ${topPost.post_id}`,
  );
  setText("top-post-views", formatCompact(topPost.views));
  setText("top-post-engagement", formatPercent(topPost.engagement_rate));
  setText("top-post-watch", formatPercent(topPost.average_watch_ratio));
  setText(
    "top-post-signal",
    topPost.signals.length
      ? topPost.signals
          .join(" · ")
          .replaceAll("_", " ")
          .replace(/^./, (character) => character.toUpperCase())
      : "Top performer",
  );
  buildPostRows(posts);

  setText(
    "repeat-title",
    `Retest ${strategy.repeat.format}: ${strategy.repeat.topic || "strongest supported topic"}.`,
  );
  setText("repeat-copy", strategy.primary_goal);
  setText("repeat-count", formatPostCount(signals.repeat_post_ids.length));
  setText("repeat-ids", formatIds(signals.repeat_post_ids));

  setText("retention-copy", strategy.retention_adjustment.guidance);
  setText(
    "retention-count",
    formatPostCount(signals.weak_retention_post_ids.length),
  );
  setText("retention-ids", formatIds(signals.weak_retention_post_ids));

  const firstPause = strategy.pause[0];
  setText(
    "pause-title",
    firstPause ? `Revise ${firstPause.format}.` : "No direct pauses recommended.",
  );
  setText(
    "pause-copy",
    firstPause
      ? `${firstPause.action} ${firstPause.reason}`
      : "No post met the current pause-candidate rule.",
  );
  setText("pause-count", formatPostCount(signals.pause_post_ids.length));
  setText("pause-ids", formatIds(signals.pause_post_ids));

  setText("recommendation-title", item.working_title);
  setText("primary-goal", strategy.primary_goal);
  setText("recommendation-format", item.format);
  setText("recommendation-topic", item.topic || "Unavailable");
  setText("recommendation-evidence", item.source_post_id);
  setText("recommendation-provider", providerLabel);
  setText("creative-direction", item.creative_direction);
  setText("retention-guidance", strategy.retention_adjustment.guidance);

  setText("script-title", item.topic || item.working_title);
  setText("script-hook", data.script.hook);
  replaceList("script-body", data.script.body, "li");
  setText("script-cta", data.script.cta);
  setText("caption-copy", data.caption);
  replaceList("hashtag-copy", data.hashtags, "span");
  replaceList("review-checks", data.human_review_note || [], "li");

  setText(
    "footer-data-note",
    `${sourceName} · ${providerLabel} · No automatic publishing`,
  );

  const planLink = document.getElementById("plan-link");
  const metricsLink = document.getElementById("metrics-link");

  if (planLink) {
    planLink.href = `../../${data.content_plan_path}`;
    planLink.textContent = "View latest plan";
  }

  if (metricsLink) {
    metricsLink.href = `../../${data.metrics_summary.path}`;
  }

  document.body.classList.remove("output-missing");
  document.getElementById("missing-output")?.setAttribute("hidden", "");
}

async function loadDashboard() {
  try {
    let response = await fetch("/api/dashboard-data", { cache: "no-store" });

    if (!response.ok) {
      response = await fetch("../../outputs/latest/dashboard_data.json", {
        cache: "no-store",
      });
    }

    if (!response.ok) {
      return;
    }

    const data = await response.json();

    if (validateDashboardData(data)) {
      renderDashboard(data);
    }
  } catch {
    // Keep the explicit missing-output state for file:// or unavailable data.
  }
}

loadDashboard();

const analystForm = document.getElementById("analyst-form");
const analystQuestion = document.getElementById("analyst-question");
const analystClear = document.getElementById("analyst-clear");
const analystProvider = document.getElementById("analyst-provider");

if (analystForm && analystQuestion) {
  analystForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!latestDashboardData) {
      setText(
        "analyst-status",
        "Run the backend pipeline first, then refresh this dashboard.",
      );
      return;
    }

    const question = analystQuestion.value;
    const provider = analystProvider ? analystProvider.value : "manual";

    if (!question.trim()) {
      setText("analyst-status", "Enter a question before asking the analyst.");
      return;
    }

    setText("analyst-status", "Sending question to the analyst server...");

    try {
      const response = await fetch("/api/analyst-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, provider }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(
          error.detail ||
            "The analyst server could not answer from the latest run.",
        );
      }

      const answer = await response.json();
      renderAnalystAnswer(answer);
      setText("analyst-status", "Answer ready");
    } catch (error) {
      setText(
        "analyst-status",
        error instanceof Error
          ? error.message
          : "Start the FastAPI server with python3 -m src.backend.server.",
      );
    }
  });
}

if (analystClear) {
  analystClear.addEventListener("click", () => {
    if (analystQuestion) {
      analystQuestion.value = "";
    }

    setText("answer-summary", "Ask a question to generate a structured analysis.");
    replaceList("answer-evidence", [], "li");
    setText("answer-recommendation", "No answer yet.");
    setText("answer-next-action", "No action yet.");
    replaceList("answer-limitations", [], "li");
    renderAnalystTrace(null);
    setText("analyst-status", "Ready");
  });
}

const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector("#site-navigation");

if (menuButton && navigation) {
  menuButton.addEventListener("click", () => {
    const isOpen = navigation.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });

  navigation.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      navigation.classList.remove("open");
      menuButton.setAttribute("aria-expanded", "false");
    }
  });
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const targetId = button.getAttribute("data-copy-target");
    const target = targetId ? document.getElementById(targetId) : null;

    if (!target) {
      return;
    }

    const originalLabel = button.textContent;
    const text = target.innerText.trim();

    try {
      await navigator.clipboard.writeText(text);
      button.textContent = "Copied";
    } catch {
      button.textContent = "Select text";
    }

    window.setTimeout(() => {
      button.textContent = originalLabel;
    }, 1800);
  });
});
