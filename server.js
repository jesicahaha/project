const express = require('express');
const { Server } = require('socket.io');

const app = express();
app.use(express.static('www'));

const server = app.listen(3000, '0.0.0.0', () => {
  console.log('Server running on http://localhost:3000/client.html');
})

const io = new Server(server);

io.on('connection', (socket) => {
  console.log('新使用者連線');
  socket.emit('eventName', { msg: 'Connection Ready！' });

  socket.on('user', (data) => {
    console.log('user:' + data.text);
    socket.emit('eventName', { msg: '後端收到第' + data.count + '次！' });
  });
});
