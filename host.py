from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from queue import Queue

from yahtzee import yahtzee

import asyncio
import pyshark
import socket
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

# TCP server details
TCP_HOST = '127.0.0.1'
TCP_PORT = 8888

client_socket = None
tcp_client = None

server_queue = Queue()
wire_queue = Queue()

# Wireshark style packet capture
def packet_capture(queue):
    asyncio.set_event_loop(asyncio.new_event_loop())

    # Windows loopback interface
    interface = r'\Device\NPF_Loopback'  
    # TCP Server filter
    bpf_filter = 'tcp port 8888' 


    start_time = time.time()
    capture = pyshark.LiveCapture(interface=interface, bpf_filter=bpf_filter)
    try:
        for packet in capture.sniff_continuously():
            now = time.time() - start_time #Option date stamp, I prefer time in seconds. {str(packet.sniff_time).ljust(8)}
            prot = "TCP" #packet.ip.proto gives int, we know its TCP so overriding it
            ports = f'{packet.tcp.srcport} → {packet.tcp.dstport}'

            tcp = packet.tcp

            flags = []
            if tcp.flags_ack.raw_value == "1":
                flags.append("ACK")
            if tcp.flags_syn.raw_value == "1":
                flags.append("SYN")
            if tcp.flags_fin.raw_value == "1":
                flags.append("FIN")
            if tcp.flags_push.raw_value == "1":
                flags.append("PSH")

            # Wireshark "Info" column
            flags_str = "[" + " ".join(flags) + "]" if flags else ""
            seq = tcp.seq
            ack = tcp.ack
            win = tcp.window_size_value
            length = packet.length
            info_str = f"{flags_str} Seq={seq} Ack={ack} Win={win} Len={length}"
            
            raw_bytes = ""
            if hasattr(tcp, 'payload'):
                raw_hex = tcp.payload.replace(':', '')
                raw_bytes = bytes.fromhex(raw_hex)
                if len(raw_bytes) > 40:
                    raw_bytes = raw_bytes[:37] + b'...'
                

            queue.put(f'| {str(packet.number).ljust(3)} | {str(int(now*10000)/10000).ljust(8)} | {packet.ip.src.ljust(15)} | {packet.ip.dst.ljust(15)} | {prot.ljust(8)} | {str(packet.length).ljust(6)} | {ports.ljust(15)} | {info_str.ljust(40)} | {raw_bytes}')
            
    except KeyboardInterrupt:
        queue.put("Capture interrupted by user.")



def handle_client(client_socket, client_address, queue):
    queue.put(f"Started thread to handle {client_address}")
    game = yahtzee()
    try:
        client_socket.sendall(b"Welcome to Yahtzee!\n")
        while True:
            client_socket.sendall(b'Enter command ("help" for availible commands):\r\n')
            data = client_socket.recv(1024)
            if not data:
                break
            msg = data.decode('utf-8').strip().lower().split()
            queue.put(f'Recieved from client: {msg}')
            command = msg[0]
            args = msg[1:]
            response = ""

            if command in ("help", "?"):
                response = (
                    "Commands:\n"
                    "  roll [1-5]...   Roll dice (optionally specify dice to reroll i.e roll 1 2 4)\n"
                    "  score ?         Show available score categories\n"
                    "  score [n]       Score the current dice in category number n\n"
                    "  new             Start a new game\n"
                )
                
            if command == "roll":
                if args == []:
                    response = str(game.next_roll())
                try:
                    indices = [int(i) - 1 for i in args]
                    if all(0 <= i <= 4 for i in indices):
                        reroll = [i in indices for i in range(5)]
                        game.set_reroll(reroll)
                        response = str(game.next_roll())
                    else:
                        response = "Invalid Input: Dice must be between 0 and 4\n"
                except ValueError:
                    response = "Invalid Input: Dice must be numbers\n"

            if command == "score":
                if args and args[0] == '?':
                    response = game.get_available_scores()
                elif args:
                    try:
                        choice = int(args[0])
                        if 1 <= choice <= 13:
                            response = game.score_dice(choice - 1)
                            
                        else:
                            response = "Invalid Input: Number outside of bounds\n"
                    except ValueError:
                        response = "Invalid Input: Not a number\n"
                else:
                    response = "Invalid Input: No argument specified\n"

            if command == "new":
                game.new_game()
                response = "Welcome to Yahtzee!\n"

            client_socket.sendall(response.encode('utf-8') + b'\n')
    
    except Exception as e:
        queue.put(f"Error with client {client_address}: {e}")
    finally:
        client_socket.close()
        queue.put(f"Closed connection to {client_address}")

def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((TCP_HOST, TCP_PORT))
    server_socket.listen(5)

    print(f"Server listening on {TCP_HOST}:{TCP_PORT}")
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Accepted connection from {client_address}")

            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, server_queue))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server_socket.close()

def tcp_client_thread():
    global client_socket
    try:
        time.sleep(2) #delay so page loads before client starts
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((TCP_HOST, TCP_PORT))

        while True:
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                break
            socketio.emit('client_log', {'data': data})

    except Exception as e:
        print(f"TCP client error: {e}")
        socketio.emit('client_log', {'data': f"Error: {e}"})

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():    
    global tcp_client
    if tcp_client is None:
        tcp_client = threading.Thread(target=tcp_client_thread)
        tcp_client.daemon = True
        tcp_client.start()

@socketio.on('send_command')
def handle_command(message):
    try:
        if client_socket:
            client_socket.sendall(message['data'].encode('utf-8'))
    except Exception as e:
        emit('client_log', {'data': f"Send error: {e}"})

def emit_server_logs():
    while True:
        if not server_queue.empty():
            log_message = server_queue.get()
            socketio.emit('server_log', {'data': log_message})
        socketio.sleep(0.5)

def emit_packet_capture():
    while True:
        if not wire_queue.empty():
            log_message = wire_queue.get()
            socketio.emit('wire_log', {'data': log_message})
        socketio.sleep(0.5)

if __name__ == '__main__':
    # Start TCP server thread
    tcp_server = threading.Thread(target=run_server)
    tcp_server.daemon = True
    tcp_server.start()

    # Start the TCP server log emitter
    socketio.start_background_task(emit_server_logs)

    
    # Start packet capture thread
    packet = threading.Thread(target=packet_capture, args=[wire_queue])
    packet.daemon = True
    packet.start()

    # Start the background packet capture emitter
    socketio.start_background_task(emit_packet_capture)

    # Start webserver
    socketio.run(app, host='0.0.0.0', port=5000)
