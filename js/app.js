let matchIndex = [];
let teamMatchStats = [];

const metricDefinitions = [
  { key: "goals", label: "Goals" },
  { key: "own_goals", label: "Own Goals" },
  { key: "shots", label: "Shots" },
  { key: "passes", label: "Passes" },
  { key: "dribbles", label: "Dribbles" },
  { key: "fouls", label: "Fouls" },
  { key: "yellow_cards", label: "Yellow Cards" },
  { key: "red_cards", label: "Red Cards" },
  { key: "corners", label: "Corners" },
  { key: "free_kicks", label: "Free Kicks" },
  { key: "goal_kicks", label: "Goal Kicks" },
  { key: "throw_ins", label: "Throw-ins" },
  { key: "penalty_shots", label: "Penalty Shots" },
  { key: "offsides", label: "Offsides" },
];

function getElement(id) {
  return document.getElementById(id);
}

async function fetchJson(path) {
  const response = await fetch(path);

  if (!response.ok) {
    throw new Error(`Could not load ${path}. HTTP ${response.status}`);
  }

  return response.json();
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort();
}

function populateSelect(selectId, values, includeAll = false) {
  const select = getElement(selectId);
  select.innerHTML = "";

  if (includeAll) {
    const option = document.createElement("option");
    option.value = "all";
    option.textContent = "All";
    select.appendChild(option);
  }

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function populateInitialFilters() {
  const competitions = uniqueSorted(
    teamMatchStats.map((row) => row.competition_name)
  );

  populateSelect("competition-filter", competitions, true);
  populateSeasonFilter();
  populateTeamFilter();
}

function populateSeasonFilter() {
  const selectedCompetition = getElement("competition-filter").value;

  const filteredRows = teamMatchStats.filter((row) => {
    return (
      selectedCompetition === "all" ||
      row.competition_name === selectedCompetition
    );
  });

  const seasons = uniqueSorted(filteredRows.map((row) => row.season_name));

  populateSelect("season-filter", seasons, true);
}

function populateTeamFilter() {
  const selectedCompetition = getElement("competition-filter").value;
  const selectedSeason = getElement("season-filter").value;

  const filteredRows = teamMatchStats.filter((row) => {
    const competitionOk =
      selectedCompetition === "all" ||
      row.competition_name === selectedCompetition;

    const seasonOk =
      selectedSeason === "all" || row.season_name === selectedSeason;

    return competitionOk && seasonOk;
  });

  const teams = uniqueSorted(filteredRows.map((row) => row.team));

  populateSelect("team-filter", teams, false);
}

function getFilteredRows() {
  const selectedCompetition = getElement("competition-filter").value;
  const selectedSeason = getElement("season-filter").value;
  const selectedTeam = getElement("team-filter").value;
  const lastX = getElement("last-x-filter").value;

  let rows = teamMatchStats.filter((row) => {
    const competitionOk =
      selectedCompetition === "all" ||
      row.competition_name === selectedCompetition;

    const seasonOk =
      selectedSeason === "all" || row.season_name === selectedSeason;

    const teamOk = !selectedTeam || row.team === selectedTeam;

    return competitionOk && seasonOk && teamOk;
  });

  rows.sort((a, b) => {
    const dateCompare = new Date(b.match_date) - new Date(a.match_date);

    if (dateCompare !== 0) {
      return dateCompare;
    }

    return Number(b.match_id) - Number(a.match_id);
  });

  if (lastX !== "all") {
    rows = rows.slice(0, Number(lastX));
  }

  return rows;
}

function calculateMetricSummary(rows) {
  const matchCount = rows.length;

  return metricDefinitions.map((metric) => {
    const total = rows.reduce((sum, row) => {
      return sum + Number(row[metric.key] || 0);
    }, 0);

    const average = matchCount > 0 ? total / matchCount : 0;

    return {
      key: metric.key,
      label: metric.label,
      total,
      average,
    };
  });
}

function renderSummary(rows) {
  const summary = getElement("summary");
  const selectedTeam = getElement("team-filter").value;

  if (rows.length === 0) {
    summary.textContent = "No matches found for the selected filters.";
    return;
  }

  const firstDate = rows[rows.length - 1].match_date;
  const lastDate = rows[0].match_date;

  summary.textContent = `${selectedTeam}: ${rows.length} match(es), from ${firstDate} to ${lastDate}.`;
}

function renderMetricsTable(rows) {
  const tableBody = getElement("metrics-table-body");
  const metrics = calculateMetricSummary(rows);

  tableBody.innerHTML = "";

  metrics.forEach((metric) => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${metric.label}</td>
      <td>${metric.total}</td>
      <td>${metric.average.toFixed(2)}</td>
    `;

    tableBody.appendChild(row);
  });
}

function renderMatchesTable(rows) {
  const tableBody = getElement("matches-table-body");
  tableBody.innerHTML = "";

  rows.forEach((match) => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${match.match_date ?? ""}</td>
      <td>${match.competition_name ?? ""}</td>
      <td>${match.season_name ?? ""}</td>
      <td>${match.team ?? ""}</td>
      <td>${match.opponent ?? ""}</td>
      <td>${match.home_away ?? ""}</td>
      <td>${match.goals ?? 0}</td>
      <td>${match.shots ?? 0}</td>
      <td>${match.passes ?? 0}</td>
      <td>${match.fouls ?? 0}</td>
    `;

    tableBody.appendChild(row);
  });
}

function renderDashboard() {
  const rows = getFilteredRows();

  renderSummary(rows);
  renderMetricsTable(rows);
  renderMatchesTable(rows);
}

function bindEvents() {
  getElement("competition-filter").addEventListener("change", () => {
    populateSeasonFilter();
    populateTeamFilter();
    renderDashboard();
  });

  getElement("season-filter").addEventListener("change", () => {
    populateTeamFilter();
    renderDashboard();
  });

  getElement("team-filter").addEventListener("change", renderDashboard);
  getElement("last-x-filter").addEventListener("change", renderDashboard);
}

async function init() {
  const status = getElement("status");

  try {
    status.textContent = "Loading analytical data...";

    matchIndex = await fetchJson("./data/match_index.json");
    teamMatchStats = await fetchJson("./data/team_match_stats.json");

    status.textContent = `Loaded ${matchIndex.length} matches and ${teamMatchStats.length} team-match rows.`;

    populateInitialFilters();
    bindEvents();
    renderDashboard();
  } catch (error) {
    status.textContent =
      "Could not load analytical data. Confirm that match_index.json and team_match_stats.json exist in the data folder.";
    console.error(error);
  }
}

init();
