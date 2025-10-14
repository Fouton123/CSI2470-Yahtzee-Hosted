from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
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
# Windows loopback interface
INTERFACE = r'\Device\NPF_Loopback'  

client_sockets = {}

server_queue = Queue()
wire_queue = Queue()

# Wireshark style packet capture
def packet_capture(queue):
    asyncio.set_event_loop(asyncio.new_event_loop())

    # TCP Server filter
    bpf_filter = 'tcp port 8888' 

    start_time = time.time()
    capture = pyshark.LiveCapture(interface=INTERFACE, bpf_filter=bpf_filter)
    try:
        for packet in capture.sniff_continuously():
            now = time.time() - start_time # Option date stamp, I prefer time in seconds. {str(packet.sniff_time).ljust(8)}
            prot = "TCP" # packet.ip.proto gives int, we know its TCP so overriding it
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
            
            # Rawdata column
            raw_hex = ""
            if hasattr(tcp, 'payload'):
                raw_hex = tcp.payload.replace(':', '')
                raw_bytes = bytes.fromhex(raw_hex)
                if len(raw_hex) > 40:
                    raw_hex = raw_hex[:37] + '...'
                
            # Specifiy the client port for client filter in webpage
            port = int(packet.tcp.srcport)
            if port == 8888:
                port = int(packet.tcp.dstport)
            trace = f'| {str(packet.number).ljust(3)} | {str(int(now*10000)/10000).ljust(12)} | {packet.ip.src.ljust(13)} | {packet.ip.dst.ljust(13)} | {prot.ljust(8)} | {str(packet.length).ljust(6)} | {ports.ljust(15)} | {info_str.ljust(43)} | {raw_hex}'
            queue.put([trace, port])
            
    except KeyboardInterrupt:
        queue.put("Capture interrupted by user.")


# Yahtzee client
# Handles the game controls and hosts the game
def handle_client(client_socket, client_address, queue, sid):
    queue.put([f"Started thread to handle {client_address}", sid])
    game = yahtzee()
    try:
        client_socket.sendall(b"Welcome to Yahtzee!\n")
        while True:
            client_socket.sendall(b'Enter command ("help" for available commands):\r\n')
            data = client_socket.recv(1024)
            if not data:
                break
            msg = data.decode('utf-8').strip().lower().split()
            queue.put([f'Received from client: {msg}', sid])
            command = msg[0]
            args = msg[1:]
            response = ""

            if command in ("help", "?"):
                response = (
                    "Commands:\n"
                    "  roll            Roll all dice\n"
                    "  roll [1-5]...   Roll dice (optionally specify dice to reroll i.e roll 1 2 4)\n"
                    "  score ?         Show available score categories\n"
                    "  score [n]       Score the current dice in category number n\n"
                    "  new             Start a new game\n"
                )
                
            elif command == "roll":
                try:
                    if not args:
                        response = str(game.next_roll())
                    else:
                        indices = [int(i) - 1 for i in args]
                        if all(0 <= i <= 4 for i in indices):
                            reroll = [i in indices for i in range(5)]
                            game.set_reroll(reroll)
                            response = str(game.next_roll())
                        else:
                            response = "Invalid Input: Dice must be between 1 and 5\n"
                except ValueError:
                    response = "Invalid Input: Dice must be numbers\n"

            elif command == "score":
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

            elif command == "new":
                game.new_game()
                response = "Welcome to Yahtzee!\n"
            
            else:
                response = "Unknown command. Type 'help' for available commands.\n"
                
            client_socket.sendall(response.encode('utf-8') + b'\n')
    
    except Exception as e:
        queue.put(f"Error with client {client_address}: {e}")
    finally:
        client_socket.close()
        queue.put(f"Closed connection to {client_address}")

# Yahtzee server
# Watches for new connections and connects it to a new Yahtzee client
def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((TCP_HOST, TCP_PORT))
    server_socket.listen(5)

    print(f"Server listening on {TCP_HOST}:{TCP_PORT}")
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Accepted connection from {client_address}")
            tmpsid = client_socket.recv(1024).decode('utf-8') # Receive the sid of the connected client for room isolation
            if "SID:" in tmpsid:
                sid = tmpsid.replace("SID:", "")
                client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, server_queue, sid))
                client_thread.daemon = True
                client_thread.start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    finally:
        server_socket.close()

def tcp_client_thread(sid):
    try:
        time.sleep(2) # Delay so page loads before client starts
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TCP_HOST, TCP_PORT))
        msg = f'SID:{sid}' # Send sid for room isolation on server side
        sock.sendall(msg.encode('utf-8'))
        client_sockets[sid] = sock

        socketio.emit('connection', {'port': sock.getsockname()[1]}, room=sid) # Send port to webpage for packet filtering

        while True:
            data = sock.recv(4096).decode('utf-8')
            if not data:
                break
            socketio.emit('client_log', {'data': data}, room=sid)

    except Exception as e:
        print(f"TCP client error: {e}")
        socketio.emit('client_log', {'data': f"Error: {e}"}, room=sid)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(request.remote_addr)
    join_room(sid)
    thread = threading.Thread(target=tcp_client_thread, args=(sid,))
    thread.daemon = True
    thread.start()

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    leave_room(sid)
    if sid in client_sockets:
        try:
            client_sockets[sid].close()
        except:
            pass
        del client_sockets[sid]

@socketio.on('send_command')
def handle_command(message):
    sid = request.sid
    try:
        if sid in client_sockets:
            client_sockets[sid].sendall(message['data'].encode('utf-8'))
    except Exception as e:
        emit('client_log', {'data': f"Send error: {e}"}, room=sid)

def emit_server_logs():
    while True:
        if not server_queue.empty():
            log_message = server_queue.get()
            socketio.emit('server_log', {'data': log_message[0]}, room=log_message[1])
        socketio.sleep(0.5)

def emit_packet_capture():
    while True:
        if not wire_queue.empty():
            log_message = wire_queue.get()
            socketio.emit('wire_log', {'data': log_message[0], 'port': log_message[1]})
        socketio.sleep(0.5)

def start_thread(target, *args):
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread

if __name__ == '__main__':
    # Start TCP server thread
    start_thread(run_server)

    # Start the TCP server log emitter
    socketio.start_background_task(emit_server_logs)

    
    # Start packet capture thread
    start_thread(packet_capture, wire_queue)

    # Start the background packet capture emitter
    socketio.start_background_task(emit_packet_capture)

    # Start webserver
    socketio.run(app, host='0.0.0.0', port=80)
