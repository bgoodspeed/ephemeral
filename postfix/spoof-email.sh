echo -ne 'helo localhost\r\nmail from: SPOOFEDEMAILFROM\r\nrcpt to: SPOOFEDEMAILTO\r\ndata\r\nSubject:spoof\r\nThis is a spoofed message\r\n.\r\nquit\r\n' | nc localhost 25
