async function loadCompetitions() {
  const status = document.getElementById("status");
  const tableBody = document.getElementById("competitions-table-body");

  try {
    const response = await fetch("./data/competitions_national.json");

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const competitions = await response.json();

    status.textContent = `Loaded ${competitions.length} national competition/season rows.`;

    tableBody.innerHTML = "";

    competitions.forEach((c) => {
      const row = document.createElement("tr");

      row.innerHTML = `
        <td>${c.competition_name ?? ""}</td>
        <td>${c.season_name ?? ""}</td>
        <td>${c.competition_gender ?? ""}</td>
        <td>${c.country_name ?? ""}</td>
        <td>${c.match_available ?? ""}</td>
      `;

      tableBody.appendChild(row);
    });
  } catch (error) {
    status.textContent =
      "Could not load data/competitions_national.json. Run the GitHub Action first.";
    console.error(error);
  }
}

loadCompetitions();
