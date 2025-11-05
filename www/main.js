var socket = io.connect();
var i = 1;
socket.on('eventName', function(data) {
    // Client 端接收到由 Server 端接發出的 eventName 事件
    $('#resBackEnd').append(
        '<div class="alert alert-warning" role="alert">' +
        data.msg +
        '</div>',
    );
    console.log(data.msg);
});

// 送出訊息到 server
$('#sendMsg').on('click', function() {
    inputVal = $('#textInput').val();
    count = i++;
    socket.emit('user', {
        // Client 端 送出 User 事件
        text: inputVal,
        count: count,
    });
});


// ===== 語音辨識 =====
let recognition;
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'zh-TW';      // 語言：中文
    recognition.interimResults = false; // 只取最終結果

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        console.log('辨識文字：', transcript);
        const count = i++;
        // 傳給 server
        socket.emit('user', {
            text: transcript,
            count: count,
        });
        // 顯示在畫面上
        $('#textInput').val(transcript);
    };

    recognition.onerror = (event) => {
        console.error('語音辨識錯誤', event.error);
    };

    recognition.onend = () => {
        console.log('語音辨識結束');
    };
} else {
    alert('您的瀏覽器不支援語音辨識');
}

// 開始錄音辨識
$('#startRecord').on('click', function() {
    if (recognition) recognition.start();
});

// 停止辨識（可選）
$('#stopRecord').on('click', function() {
    if (recognition) recognition.stop();
});

// ===== 語音辨識 =====