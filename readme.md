# Installation & Setup Guide
## Live Demo (No Installation Required)
If you prefer not to install and run the project locally, you can try the hosted version at:
[erickausch.con](https://erickausch.com)

This demo allows you to experience the program’s features directly in your browser without setting up any dependencies.

## **How to Install Necessary Packages**

1. **Open Command Prompt**
2. Run the following command to install or update PIP:

   ```bash
   python -m ensurepip --upgrade
   ```
3. Install **pyshark**:

   ```bash
   pip install pyshark
   ```
4. Install **Flask**:

   ```bash
   pip install Flask
   ```
5. Install **Flask-SocketIO**:

   ```bash
   pip install flask flask-socketio
   ```

You are now ready to run the project!



## **Running the Project**

1. **Open Command Prompt**
2. Navigate to or type the full path to the project’s `host.py` file.
   Example:

   ```bash
    python host.py
   ```
3. Open the webpage:

   ```
   http://127.0.0.1/
   ```

You are now hosting the project and acting as a client!

---

## Team Contributions

### **Damian**
- Explained the program’s networking workflow (HTTP/TCP/WebSocket)
- Analyzed traffic with Wireshark and broke down communication layer-by-layer
- Wrote the **Network Analysis** section of the presentation

### **Eric**
- Developed the Yahtzee and webserver systems
- Implemented networking features and fixed team-reported bugs
- Wrote the **Program Structure** section of the presentation

### **Garrett**
- Found and reported key Yahtzee application bugs and suggested user-experience improvements
- Wrote the **How To Use** guide
- Wrote the **Debugging** section of the presentation

### **Justin**
- Wrote the **Program Operation** section of the presentation
- Found and reported key Yahtzee application bugs
