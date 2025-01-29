// Hàm vẽ biểu đồ nến

new TradingView.widget(
    {
        "autosize": true,
        "symbol": "BINANCE:BTCUSDT",
        "interval": "240",
        "timezzone": "Etc/Utc",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": true,
        "withdateranges": false,
        "hide_side_toolbar": true,
        "allow_symbol_change": true,
        "watchlist": [
            "BINANCE:BTCUSDT",
            "BINANCE:ETHUSDT"
        ],
        "details": true,
        "hotlist": true,
        "calendar": true,
        "studies": [
            "STD;SMA"
        ],
        "container_id": "chart",
        "show_popup_button": true,
        "popup_width": "1000",
        "popup_height": "650"
    }
);

// function setupClickEvents() {
//     const cryptos = document.querySelectorAll("table tr td:nth-child(1)");

//     cryptos.forEach(crypto => {
//         crypto.addEventListener("click", async (e) => {
//             const symbol = e.target.innerText.trim().toUpperCase(); // Lấy tên đồng tiền
//             await drawCandlestickChart("TSMC"); // Gọi hàm vẽ biểu đồ
//         });
//     });
// }

// // Khởi tạo
// document.addEventListener("DOMContentLoaded", () => {
//     setupClickEvents();
// });