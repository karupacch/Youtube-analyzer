const useSheetsCheckbox = document.getElementById('use_sheets_integration');
const submitButton = document.getElementById('submit_button');

// チェックボックスの状態に基づいてボタンのテキストを更新する関数
function updateButtonText() {
    if (useSheetsCheckbox.checked) {
        submitButton.textContent = '動画を検索しスプレッドシートに出力';
    } else {
        submitButton.textContent = '動画を検索しCSVをダウンロード';
    }
}

// ページロード時とチェックボックスの状態が変わった時にボタンのテキストを更新
updateButtonText(); // 初期表示時の設定
useSheetsCheckbox.addEventListener('change', updateButtonText);