function trackTaianeDamanga() {
  // Configuration
  const WORLD = "SeuMundo";          // Ex: "Antica", "Calmera"
  const CATEGORY = "experience";     // Geralmente "experience"
  const VOCATION = "druid";          // "knight", "paladin", "sorcerer", "druid" ou "all"
  const CHARACTER_NAME = "Nome Do Personagem";  // Exato como aparece no jogo
  const START_PAGE = 1;
  const END_PAGE = 4;                // Ajuste conforme necessário para encontrar o personagem
  const SPREADSHEET_ID = "ID_DA_SUA_PLANILHA";  // Encontrado na URL do Google Sheets
  const SHEET_NAME = "Dados";        // Nome da aba onde os dados serão salvos
  const TIMEZONE = "GMT-3";          // Ajuste para seu fuso (ex: "GMT-3" para Brasil)

  // Access the spreadsheet and sheet
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);

  // Create sheet and add headers if it doesn't exist
  if (!sheet) {
    sheet = spreadsheet.insertSheet(SHEET_NAME);
    sheet.appendRow(["Date", "Name", "Vocation", "Level", "Experience"]);
  } else if (sheet.getLastRow() === 0) {
    sheet.appendRow(["Date", "Name", "Vocation", "Level", "Experience"]);
  }

  // Iterate through pages 1 to 10
  for (let page = START_PAGE; page <= END_PAGE; page++) {
    try {
      // Construct and fetch API URL
      const url = `https://dev.tibiadata.com/v4/highscores/${WORLD}/${CATEGORY}/${VOCATION}/${page}`;
      const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
      if (response.getResponseCode() !== 200) {
        Logger.log(`Error fetching page ${page}: HTTP ${response.getResponseCode()}`);
        continue;
      }

      // Parse JSON response
      const data = JSON.parse(response.getContentText());
      const highscores = data.highscores?.highscore_list;

      if (!highscores || !Array.isArray(highscores)) {
        Logger.log(`No highscore list on page ${page}`);
        continue;
      }

      // Search for the character
      for (let entry of highscores) {
        if (entry.name.toLowerCase() === CHARACTER_NAME.toLowerCase()) {
          // Format date as dd-mm-yyyy
          const date = new Date();
          const formattedDate = Utilities.formatDate(date, TIMEZONE, "dd-MM-yyyy");

          // Log data to sheet
          const row = [
            formattedDate,
            entry.name,
            entry.vocation,
            entry.level,
            entry.value // Experience points
          ];
          sheet.appendRow(row);
          Logger.log(`Logged data for ${entry.name} on page ${page}`);
          return; // Exit after logging
        }
      }
    } catch (error) {
      Logger.log(`Error on page ${page}: ${error.message}`);
      continue;
    }
  }

  Logger.log(`Character ${CHARACTER_NAME} not found in pages ${START_PAGE} to ${END_PAGE}`);
}

// Set up a daily trigger
function createDailyTrigger() {
  ScriptApp.newTrigger("trackTaianeDamanga")
    .timeBased()
    .everyDays(1)
    .atHour(8) // Runs daily at 8 AM (adjust as needed)
    .create();
}