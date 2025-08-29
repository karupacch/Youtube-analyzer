// Vue.js アプリケーションの作成
const app = Vue.createApp({
    data() {
        return {
            useSheetsIntegration: false, // チェックボックスの初期状態
        };
    },
    computed: {
        submitButtonText() {
            return this.useSheetsIntegration ? '動画を検索しスプレッドシートに出力' : '動画を検索しCSVをダウンロード';
        }
    },
    mounted() {
        // ページロード時にチェックボックスの初期状態を反映
        const checkbox = document.getElementById('use_sheets_integration');
        if (checkbox) {
            this.useSheetsIntegration = checkbox.checked;
        }
    }
});

// VueアプリケーションをHTML要素にマウント
app.mount('#app'); // #appというIDを持つ要素にマウントすることを想定