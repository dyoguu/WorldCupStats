let matchIndex = [];
let teamMatchStats = [];
let teamMatchMinuteStats = [];
let eventCache = new Map();

const STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data";

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

const kpiMetrics = ["goals", "shots", "passes", "fouls", "corners", "yellow_cards"];

function getElement(id) { return document.getElementById(id); }

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}. HTTP ${response.status}`);
  return response.json();
}

function uniqueSorted(values) { return [...new Set(values.filter(Boolean))].sort(); }
function getSelectedValues(selectId) { return Array.from(getElement(selectId).selectedOptions).map((option) => option.value); }
function isAllSelected(selectId) { const selected = getSelectedValues(selectId); return selected.length === 0 || selected.includes("all"); }
function valueMatchesSelection(value, selectId) { return isAllSelected(selectId) || getSelectedValues(selectId).includes(String(value)); }

function populateMultiSelect(selectId, values, keepSelected = true) {
  const select = getElement(selectId);
  const previousSelected = keepSelected ? getSelectedValues(selectId) : [];
  select.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "all"; allOption.textContent = "All"; select.appendChild(allOption);
  values.forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; select.appendChild(option); });
  const validValues = new Set(["all", ...values.map(String)]);
  let restoredAny = false;
  previousSelected.forEach((value) => { if (validValues.has(String(value))) { const option = Array.from(select.options).find((opt) => opt.value === String(value)); if (option) { option.selected = true; restoredAny = true; } } });
  if (!restoredAny) allOption.selected = true;
}

function cleanAllSelection(selectId) {
  const select = getElement(selectId);
  const selected = getSelectedValues(selectId);
  if (selected.includes("all") && selected.length > 1) Array.from(select.options).forEach((option) => { option.selected = option.value !== "all"; });
  if (getSelectedValues(selectId).length === 0) { const allOption = Array.from(select.options).find((option) => option.value === "all"); if (allOption) allOption.selected = true; }
}

function populateInitialFilters() {
  populateMultiSelect("competition-filter", uniqueSorted(teamMatchStats.map((row) => row.competition_name)), false);
  populateSeasonFilter(); populateTeamFilter();
}
function populateSeasonFilter() { const rows = teamMatchStats.filter((row) => valueMatchesSelection(row.competition_name, "competition-filter")); populateMultiSelect("season-filter", uniqueSorted(rows.map((row) => row.season_name)), true); }
function populateTeamFilter() { const rows = teamMatchStats.filter((row) => valueMatchesSelection(row.competition_name, "competition-filter") && valueMatchesSelection(row.season_name, "season-filter")); populateMultiSelect("team-filter", uniqueSorted(rows.map((row) => row.team)), true); }

function zeroMetrics() { const obj = {}; metricDefinitions.forEach((metric) => obj[metric.key] = 0); return obj; }
function sortRowsNewestFirst(a, b) { const dateCompare = new Date(b.match_date) - new Date(a.match_date); if (dateCompare !== 0) return dateCompare; return Number(b.match_id) - Number(a.match_id); }

function applyLastX(rows) {
  const lastX = getElement("last-x-filter").value;
  if (lastX === "all") return rows;
  const x = Number(lastX);
  const rowsByTeam = new Map();
  rows.forEach((row) => { if (!rowsByTeam.has(row.team)) rowsByTeam.set(row.team, []); rowsByTeam.get(row.team).push(row); });
  const limitedRows = [];
  rowsByTeam.forEach((teamRows) => limitedRows.push(...[...teamRows].sort(sortRowsNewestFirst).slice(0, x)));
  return limitedRows.sort(sortRowsNewestFirst);
}

function getBaseFilteredWholeMatchRows() {
  let rows = teamMatchStats.filter((row) => valueMatchesSelection(row.competition_name, "competition-filter") && valueMatchesSelection(row.season_name, "season-filter") && valueMatchesSelection(row.team, "team-filter"));
  rows.sort(sortRowsNewestFirst);
  return applyLastX(rows);
}

function aggregateMinuteRowsToTeamMatch(minuteRows) {
  const grouped = new Map();
  minuteRows.forEach((row) => {
    const key = `${row.match_id}|${row.team}`;
    if (!grouped.has(key)) grouped.set(key, { match_id: row.match_id, competition_id: row.competition_id, season_id: row.season_id, competition_name: row.competition_name, season_name: row.season_name, match_date: row.match_date, team: row.team, ...zeroMetrics() });
    const target = grouped.get(key);
    metricDefinitions.forEach((metric) => target[metric.key] += Number(row[metric.key] || 0));
  });
  const wholeRowsByKey = new Map(teamMatchStats.map((row) => [`${row.match_id}|${row.team}`, row]));
  return Array.from(grouped.values()).map((row) => { const whole = wholeRowsByKey.get(`${row.match_id}|${row.team}`) || {}; return { ...row, opponent: whole.opponent || "", home_away: whole.home_away || "" }; }).sort(sortRowsNewestFirst);
}

function getBaseFilteredMinuteRows() {
  const minuteStart = Number(getElement("minute-start").value || 0);
  const minuteEnd = Number(getElement("minute-end").value || 130);
  let rows = teamMatchMinuteStats.filter((row) => valueMatchesSelection(row.competition_name, "competition-filter") && valueMatchesSelection(row.season_name, "season-filter") && valueMatchesSelection(row.team, "team-filter") && valueMatchesSelection(String(row.period), "period-filter") && Number(row.minute) >= minuteStart && Number(row.minute) <= minuteEnd);
  const selectedMatchKeys = new Set(getBaseFilteredWholeMatchRows().map((row) => `${row.match_id}|${row.team}`));
  rows = rows.filter((row) => selectedMatchKeys.has(`${row.match_id}|${row.team}`));
  return aggregateMinuteRowsToTeamMatch(rows);
}

function getFilteredRows() { return getElement("grain-filter").value === "minute_range" ? getBaseFilteredMinuteRows() : getBaseFilteredWholeMatchRows(); }

function calculateMetricSummary(rows) { const count = rows.length; return metricDefinitions.map((metric) => { const total = rows.reduce((sum, row) => sum + Number(row[metric.key] || 0), 0); return { key: metric.key, label: metric.label, total, average: count > 0 ? total / count : 0 }; }); }

function renderSummary(rows) {
  const summary = getElement("summary");
  if (rows.length === 0) { summary.textContent = "No matches found for the selected filters."; return; }
  const teamText = isAllSelected("team-filter") ? "All teams" : getSelectedValues("team-filter").join(", ");
  const firstDate = rows[rows.length - 1].match_date; const lastDate = rows[0].match_date;
  const grain = getElement("grain-filter").value === "minute_range" ? "period/minute range" : "whole match";
  summary.textContent = `${teamText}: ${rows.length} team-match row(s), ${grain}, from ${firstDate} to ${lastDate}.`;
}

function renderKpis(rows) {
  const kpiGrid = getElement("kpi-grid"); const metrics = calculateMetricSummary(rows); const metricsByKey = new Map(metrics.map((m) => [m.key, m])); kpiGrid.innerHTML = "";
  kpiMetrics.forEach((key) => { const metric = metricsByKey.get(key); if (!metric) return; const card = document.createElement("section"); card.className = "kpi-card"; card.innerHTML = `<span>${metric.label}</span><strong>${metric.average.toFixed(2)}</strong><small>Total: ${metric.total}</small>`; kpiGrid.appendChild(card); });
}

function renderMetricsTable(rows) {
  const tableBody = getElement("metrics-table-body"); const metrics = calculateMetricSummary(rows); tableBody.innerHTML = "";
  metrics.forEach((metric) => { const row = document.createElement("tr"); row.innerHTML = `<td>${metric.label}</td><td>${metric.total}</td><td>${metric.average.toFixed(2)}</td>`; tableBody.appendChild(row); });
}

function renderTeamComparison(rows) {
  const head = getElement("comparison-table-head"); const body = getElement("comparison-table-body"); const rowsByTeam = new Map();
  rows.forEach((row) => { if (!rowsByTeam.has(row.team)) rowsByTeam.set(row.team, []); rowsByTeam.get(row.team).push(row); });
  head.innerHTML = `<tr><th>Team</th><th>Matches</th>${metricDefinitions.map((m) => `<th>${m.label} Avg</th>`).join("")}</tr>`;
  body.innerHTML = "";
  Array.from(rowsByTeam.entries()).sort((a, b) => a[0].localeCompare(b[0])).forEach(([team, teamRows]) => {
    const row = document.createElement("tr");
    const metricCells = metricDefinitions.map((metric) => { const total = teamRows.reduce((sum, r) => sum + Number(r[metric.key] || 0), 0); const avg = teamRows.length > 0 ? total / teamRows.length : 0; return `<td>${avg.toFixed(2)}</td>`; }).join("");
    row.innerHTML = `<td>${team}</td><td>${teamRows.length}</td>${metricCells}`; body.appendChild(row);
  });
}

function renderMatchesTable(rows) {
  const tableBody = getElement("matches-table-body"); tableBody.innerHTML = "";
  rows.forEach((match) => { const row = document.createElement("tr"); row.innerHTML = `<td>${match.match_date ?? ""}</td><td>${match.competition_name ?? ""}</td><td>${match.season_name ?? ""}</td><td>${match.team ?? ""}</td><td>${match.opponent ?? ""}</td><td>${match.home_away ?? ""}</td><td>${match.goals ?? 0}</td><td>${match.shots ?? 0}</td><td>${match.passes ?? 0}</td><td>${match.fouls ?? 0}</td><td><button class="link-button" data-match-id="${match.match_id}">Open</button></td>`; tableBody.appendChild(row); });
  tableBody.querySelectorAll("button[data-match-id]").forEach((button) => button.addEventListener("click", () => loadMatchDetail(button.getAttribute("data-match-id"))));
}

async function loadMatchDetail(matchId) {
  const detail = getElement("match-detail"); detail.textContent = `Loading raw events for match ${matchId}...`;
  try {
    let events;
    if (eventCache.has(matchId)) events = eventCache.get(matchId);
    else { events = await fetchJson(`${STATSBOMB_BASE_URL}/events/${matchId}.json`); eventCache.set(matchId, events); }
    const match = matchIndex.find((m) => String(m.match_id) === String(matchId));
    const eventTypes = countBy(events, (event) => event.type?.name || "Unknown");
    const topEventTypes = Object.entries(eventTypes).sort((a, b) => b[1] - a[1]).slice(0, 12);
    detail.innerHTML = `<h3>${match ? `${match.home_team} ${match.home_score} - ${match.away_score} ${match.away_team}` : `Match ${matchId}`}</h3><p>${match ? `${match.competition_name} ${match.season_name} — ${match.match_date}` : ""}</p><p>Raw events loaded directly from StatsBomb: <strong>${events.length}</strong></p><h4>Top event types</h4><ul>${topEventTypes.map(([name, count]) => `<li>${name}: ${count}</li>`).join("")}</ul>`;
  } catch (error) { detail.textContent = `Could not load raw events for match ${matchId}.`; console.error(error); }
}
function countBy(items, getter) { const counts = {}; items.forEach((item) => { const key = getter(item); counts[key] = (counts[key] || 0) + 1; }); return counts; }

function renderDashboard() { const rows = getFilteredRows(); renderSummary(rows); renderKpis(rows); renderMetricsTable(rows); renderTeamComparison(rows); renderMatchesTable(rows); }
function bindEvents() {
  getElement("competition-filter").addEventListener("change", () => { cleanAllSelection("competition-filter"); populateSeasonFilter(); populateTeamFilter(); renderDashboard(); });
  getElement("season-filter").addEventListener("change", () => { cleanAllSelection("season-filter"); populateTeamFilter(); renderDashboard(); });
  getElement("team-filter").addEventListener("change", () => { cleanAllSelection("team-filter"); renderDashboard(); });
  getElement("period-filter").addEventListener("change", () => { cleanAllSelection("period-filter"); renderDashboard(); });
  ["last-x-filter", "minute-start", "minute-end", "grain-filter"].forEach((id) => getElement(id).addEventListener("change", renderDashboard));
}

async function init() {
  const status = getElement("status");
  try {
    status.textContent = "Loading analytical data...";
    matchIndex = await fetchJson("./data/match_index.json");
    teamMatchStats = await fetchJson("./data/team_match_stats.json");
    teamMatchMinuteStats = await fetchJson("./data/team_match_minute_stats.json");
    status.textContent = `Loaded ${matchIndex.length} matches, ${teamMatchStats.length} team-match rows, and ${teamMatchMinuteStats.length} minute rows.`;
    populateInitialFilters(); bindEvents(); renderDashboard();
  } catch (error) { status.textContent = "Could not load analytical data. Run the Refresh StatsBomb Data workflow and confirm the data files exist."; console.error(error); }
}
init();
