from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import json
import uuid
import os

app = FastAPI()

rooms = {}


@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()

    if room_id not in rooms:
        rooms[room_id] = {}

    room = rooms[room_id]

    existing_users = list(room.keys())

    await websocket.send_text(json.dumps({
        "type": "existing-users",
        "users": existing_users
    }))

    room[user_id] = websocket

    for uid, ws in room.items():
        if uid != user_id:
            try:
                await ws.send_text(json.dumps({
                    "type": "new-user",
                    "user_id": user_id
                }))
            except:
                pass

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            target = message.get("target")

            if target:
                if target in room:
                    await room[target].send_text(json.dumps({
                        **message,
                        "from": user_id
                    }))

            elif message.get("type") == "chat":
                for uid, ws in room.items():
                    try:
                        await ws.send_text(json.dumps({
                            "type": "chat",
                            "from": user_id,
                            "message": message.get("message", "")
                        }))
                    except:
                        pass

    except WebSocketDisconnect:
        if room_id in rooms and user_id in rooms[room_id]:
            del rooms[room_id][user_id]

            for uid, ws in rooms[room_id].items():
                try:
                    await ws.send_text(json.dumps({
                        "type": "user-left",
                        "user_id": user_id
                    }))
                except:
                    pass

            if len(rooms[room_id]) == 0:
                del rooms[room_id]


html = r"""
<!DOCTYPE html>
<html>

<head>
<meta charset="UTF-8">
<title>My Meeting</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #0f172a;
    color: white;
    font-family: Arial, sans-serif;
}

header {
    background: #111827;
    padding: 15px 25px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #334155;
}

.logo {
    font-size: 23px;
    font-weight: bold;
}

.container {
    max-width: 1300px;
    margin: auto;
    padding: 20px;
}

.join-box {
    text-align: center;
    padding: 30px;
}

input {
    padding: 13px;
    border-radius: 8px;
    border: 1px solid #475569;
    background: #1e293b;
    color: white;
    margin: 5px;
}

button {
    padding: 12px 18px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    margin: 5px;
    font-weight: bold;
}

.primary {
    background: #2563eb;
    color: white;
}

.green {
    background: #16a34a;
    color: white;
}

.red {
    background: #dc2626;
    color: white;
}

.dark {
    background: #334155;
    color: white;
}

#meeting {
    display: none;
}

.info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #111827;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 15px;
}

.videos {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 15px;
}

.video-box {
    position: relative;
    background: black;
    border-radius: 12px;
    overflow: hidden;
    min-height: 230px;
}

video {
    width: 100%;
    height: 100%;
    min-height: 230px;
    object-fit: cover;
    background: black;
}

.name {
    position: absolute;
    bottom: 8px;
    left: 8px;
    background: rgba(0,0,0,.7);
    padding: 6px 10px;
    border-radius: 6px;
}

.controls {
    text-align: center;
    background: #111827;
    padding: 12px;
    margin-top: 15px;
    border-radius: 10px;
}

.bottom {
    display: grid;
    grid-template-columns: 1fr 300px;
    gap: 15px;
    margin-top: 15px;
}

.chat {
    background: #111827;
    border-radius: 10px;
    padding: 15px;
}

#messages {
    height: 200px;
    overflow-y: auto;
    background: #020617;
    padding: 10px;
    border-radius: 8px;
}

.chat-input {
    width: calc(100% - 90px);
}

.participants {
    background: #111827;
    border-radius: 10px;
    padding: 15px;
}

@media(max-width: 800px) {
    .bottom {
        grid-template-columns: 1fr;
    }
}

</style>
</head>


<body>

<header>

<div class="logo">
🎥 My Meeting
</div>

<div>
<span id="roomDisplay"></span>
</div>

</header>


<div class="container">


<div id="joinScreen" class="join-box">

<h1>Welcome to My Meeting</h1>

<p>Create or join a meeting room</p>

<input id="nameInput" placeholder="Your name">

<br>

<input id="roomInput" placeholder="Meeting ID">

<br>

<button class="primary" onclick="joinMeeting()">
🚀 Join Meeting
</button>

</div>


<div id="meeting">


<div class="info">

<div>
Room:
<strong id="roomName"></strong>
</div>

<button class="dark" onclick="copyMeetingLink()">
🔗 Copy Meeting Link
</button>

</div>


<div id="videos" class="videos">

<div class="video-box" id="localBox">

<video id="localVideo" autoplay muted playsinline></video>

<div class="name" id="localName">
You
</div>

</div>

</div>


<div class="controls">

<button class="dark" onclick="toggleMic()" id="micBtn">
🎤 Mic
</button>

<button class="dark" onclick="toggleCamera()" id="cameraBtn">
📹 Camera
</button>

<button class="dark" onclick="shareScreen()">
🖥️ Share Screen
</button>

<button class="red" onclick="leaveMeeting()">
📞 Leave
</button>

</div>


<div class="bottom">


<div class="chat">

<h2>💬 Chat</h2>

<div id="messages"></div>

<br>

<input
id="chatInput"
class="chat-input"
placeholder="Write message..."
onkeydown="if(event.key==='Enter') sendMessage()"
>

<button class="primary" onclick="sendMessage()">
Send
</button>

</div>


<div class="participants">

<h2>👥 Participants</h2>

<div id="participantList">
You
</div>

</div>


</div>


</div>

</div>


<script>

let socket;
let localStream;
let screenStream = null;
let roomId;
let userId;
let userName;
let peers = {};
let micOn = true;
let cameraOn = true;


const rtcConfig = {

    iceServers: [
        {
            urls: "stun:stun.l.google.com:19302"
        }
    ]

};


async function joinMeeting() {

    userName =
        document.getElementById("nameInput").value.trim()
        || "Guest";

    roomId =
        document.getElementById("roomInput").value.trim();

    if (!roomId) {

        roomId =
            Math.random()
            .toString(36)
            .substring(2, 8)
            .toUpperCase();

    }

    userId =
        Math.random()
        .toString(36)
        .substring(2, 10);


    try {

        localStream =
            await navigator.mediaDevices.getUserMedia({

                video: true,
                audio: true

            });

    }

    catch(error) {

        alert(
            "Camera/Microphone permission required."
        );

        return;

    }


    document.getElementById("localVideo").srcObject =
        localStream;

    document.getElementById("localName").innerText =
        userName;


    document.getElementById("joinScreen").style.display =
        "none";

    document.getElementById("meeting").style.display =
        "block";


    document.getElementById("roomName").innerText =
        roomId;

    document.getElementById("roomDisplay").innerText =
        roomId;


    connectWebSocket();

}


function connectWebSocket() {

    const protocol =
        location.protocol === "https:"
        ? "wss"
        : "ws";

    socket =
        new WebSocket(
            protocol
            + "://"
            + location.host
            + "/ws/"
            + roomId
            + "/"
            + userId
        );


    socket.onopen = function() {

        console.log("Connected");

    };


    socket.onmessage = async function(event) {

        const data =
            JSON.parse(event.data);


        if(data.type === "existing-users") {

            for(const uid of data.users) {

                await createOffer(uid);

            }

        }


        else if(data.type === "new-user") {

            addParticipant(data.user_id);

        }


        else if(data.type === "offer") {

            await handleOffer(
                data.from,
                data.offer
            );

        }


        else if(data.type === "answer") {

            await handleAnswer(
                data.from,
                data.answer
            );

        }


        else if(data.type === "candidate") {

            await handleCandidate(
                data.from,
                data.candidate
            );

        }


        else if(data.type === "user-left") {

            removePeer(data.user_id);

        }


        else if(data.type === "chat") {

            addMessage(
                data.from === userId
                ? "You"
                : "Participant",
                data.message
            );

        }

    };

}


function createPeerConnection(remoteId) {

    if(peers[remoteId]) {

        return peers[remoteId];

    }


    const pc =
        new RTCPeerConnection(
            rtcConfig
        );


    peers[remoteId] = pc;


    localStream
        .getTracks()
        .forEach(track => {

            pc.addTrack(
                track,
                localStream
            );

        });


    pc.onicecandidate =
        function(event) {

            if(event.candidate) {

                socket.send(
                    JSON.stringify({

                        type: "candidate",

                        target: remoteId,

                        candidate:
                            event.candidate

                    })
                );

            }

        };


    pc.ontrack =
        function(event) {

            showRemoteVideo(
                remoteId,
                event.streams[0]
            );

        };


    return pc;

}


async function createOffer(remoteId) {

    const pc =
        createPeerConnection(
            remoteId
        );


    const offer =
        await pc.createOffer();


    await pc.setLocalDescription(
        offer
    );


    socket.send(
        JSON.stringify({

            type: "offer",

            target: remoteId,

            offer: offer

        })
    );

}


async function handleOffer(
    remoteId,
    offer
) {

    const pc =
        createPeerConnection(
            remoteId
        );


    await pc.setRemoteDescription(
        new RTCSessionDescription(
            offer
        )
    );


    const answer =
        await pc.createAnswer();


    await pc.setLocalDescription(
        answer
    );


    socket.send(
        JSON.stringify({

            type: "answer",

            target: remoteId,

            answer: answer

        })
    );

}


async function handleAnswer(
    remoteId,
    answer
) {

    const pc =
        peers[remoteId];

    if(!pc) return;


    await pc.setRemoteDescription(
        new RTCSessionDescription(
            answer
        )
    );

}


async function handleCandidate(
    remoteId,
    candidate
) {

    const pc =
        peers[remoteId];

    if(!pc) return;


    try {

        await pc.addIceCandidate(
            new RTCIceCandidate(
                candidate
            )
        );

    }

    catch(error) {

        console.log(error);

    }

}


function showRemoteVideo(
    remoteId,
    stream
) {

    let box =
        document.getElementById(
            "remote-" + remoteId
        );


    if(!box) {

        box =
            document.createElement("div");

        box.className =
            "video-box";

        box.id =
            "remote-" + remoteId;


        const video =
            document.createElement("video");

        video.autoplay = true;
        video.playsInline = true;
        video.srcObject =
            stream;


        const name =
            document.createElement("div");

        name.className =
            "name";

        name.innerText =
            "Participant";


        box.appendChild(video);
        box.appendChild(name);


        document
            .getElementById("videos")
            .appendChild(box);

    }

}


function addParticipant(id) {

    const list =
        document.getElementById(
            "participantList"
        );


    if(
        !document.getElementById(
            "participant-" + id
        )
    ) {

        const p =
            document.createElement("p");

        p.id =
            "participant-" + id;

        p.innerText =
            "👤 Participant";

        list.appendChild(p);

    }

}


function removePeer(id) {

    if(peers[id]) {

        peers[id].close();

        delete peers[id];

    }


    const box =
        document.getElementById(
            "remote-" + id
        );

    if(box) {

        box.remove();

    }


    const participant =
        document.getElementById(
            "participant-" + id
        );

    if(participant) {

        participant.remove();

    }

}


function toggleMic() {

    if(!localStream) return;


    micOn = !micOn;


    localStream
        .getAudioTracks()
        .forEach(track => {

            track.enabled =
                micOn;

        });


    document.getElementById("micBtn")
        .innerText =
        micOn
        ? "🎤 Mic"
        : "🔇 Mic Off";

}


function toggleCamera() {

    if(!localStream) return;


    cameraOn = !cameraOn;


    localStream
        .getVideoTracks()
        .forEach(track => {

            track.enabled =
                cameraOn;

        });


    document.getElementById("cameraBtn")
        .innerText =
        cameraOn
        ? "📹 Camera"
        : "📷 Camera Off";

}


async function shareScreen() {

    try {

        screenStream =
            await navigator.mediaDevices
            .getDisplayMedia({

                video: true

            });


        const screenTrack =
            screenStream.getVideoTracks()[0];


        for(
            const remoteId in peers
        ) {

            const sender =
                peers[remoteId]
                .getSenders()
                .find(
                    s =>
                        s.track &&
                        s.track.kind === "video"
                );


            if(sender) {

                await sender.replaceTrack(
                    screenTrack
                );

            }

        }


        document.getElementById(
            "localVideo"
        ).srcObject =
            screenStream;


        screenTrack.onended =
            stopScreenShare;

    }

    catch(error) {

        console.log(error);

    }

}


async function stopScreenShare() {

    if(!localStream) return;


    const cameraTrack =
        localStream.getVideoTracks()[0];


    for(
        const remoteId in peers
    ) {

        const sender =
            peers[remoteId]
            .getSenders()
            .find(
                s =>
                    s.track &&
                    s.track.kind === "video"
            );


        if(sender) {

            await sender.replaceTrack(
                cameraTrack
            );

        }

    }


    document.getElementById(
        "localVideo"
    ).srcObject =
        localStream;

}


function sendMessage() {

    const input =
        document.getElementById(
            "chatInput"
        );


    const message =
        input.value.trim();


    if(!message) return;


    socket.send(
        JSON.stringify({

            type: "chat",

            message: message

        })
    );


    input.value = "";

}


function addMessage(
    sender,
    message
) {

    const div =
        document.createElement("div");


    div.innerText =
        sender + ": " + message;


    document
        .getElementById("messages")
        .appendChild(div);

}


function copyMeetingLink() {

    const link =
        location.origin
        + "?room="
        + roomId;


    navigator.clipboard.writeText(
        link
    );


    alert(
        "Meeting link copied!"
    );

}


function leaveMeeting() {

    if(localStream) {

        localStream
            .getTracks()
            .forEach(
                track =>
                track.stop()
            );

    }


    for(
        const id in peers
    ) {

        peers[id].close();

    }


    if(socket) {

        socket.close();

    }


    location.reload();

}


const urlParams =
    new URLSearchParams(
        location.search
    );


const urlRoom =
    urlParams.get("room");


if(urlRoom) {

    document.getElementById(
        "roomInput"
    ).value =
        urlRoom;

}

</script>

</body>

</html>
"""


@app.get("/")
async def home():
    return HTMLResponse(html)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )