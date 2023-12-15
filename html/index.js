function parseLinks(text) {
    const markdownLinkRegex = /(\[.*?\])(\(.*\))/gm;
    const pieces = text.split(markdownLinkRegex);

    let elems = [];
    for (const piece of pieces) {
        if (piece.startsWith('(') && piece.endsWith(')')) {
            // Skip URLs of Markdown links
            continue;
        }

        const index = pieces.indexOf(piece);

        let nextPiece = "";
        if (index + 1 < pieces.length) {
            nextPiece = pieces[index + 1];
        }

        if (piece.startsWith('[') && piece.endsWith(']') && nextPiece) {
            // This piece is the link text of a markdown link
            let link = document.createElement('a');
            link.href = nextPiece.slice(1, -1);
            link.innerText = piece.slice(1, -1);
            link.target = 'blank_';
            elems.push(link);
        } else {
            // This segment is regular text
            const span = document.createElement('span');
            span.innerText = piece;
            elems.push(span);
        }
    }

    return elems;
}

function appendMessage(className, message) {
    const chatContainer = document.getElementById('chat-container');
    const messageElem = document.createElement('div');
    messageElem.className = `message ${className}`;

    const elems = parseLinks(message);
    for (elem of elems) {
        messageElem.appendChild(elem);
    }

    chatContainer.appendChild(messageElem);
    chatContainer.scrollTop = chatContainer.scrollHeight;  // Auto scroll to bottom
}

function appendContext(elem) {
    // Print error if any
    if (elem.hasOwnProperty('error_code')) {
        appendMessage('error-message', `ERROR: ${elem['error_code']}`);
    }

    // Print context message
    if (elem.hasOwnProperty('context_message')) {
        let context_message = elem["context_message"].trim();
        if (context_message !== "") {
            appendMessage('context-message', context_message);
        }
    }
}

function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value;

    if (message.trim() !== '') {
        appendMessage('user-message', message);
        chatInput.value = '';

        let xhr = new XMLHttpRequest();
        xhr.open("POST", "/chat", true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({conversation_id: "1234567890abcdef", human_input: message}));

        xhr.onload = function() {
            try {
                let response = JSON.parse(this.responseText);
                console.log(response);

                if (response.hasOwnProperty('error_code')) {
                    appendMessage('error-message', `ERROR: ${response['error_code']}`);
                }

                if (response.hasOwnProperty('results')) {
                    response['results'].forEach((elem) => appendContext(elem));
                }

                if (response.hasOwnProperty('message')) {
                    appendMessage('bot-message', response['message']);
                }
            } catch (error) {
                appendMessage('error-message', "ERROR: Something went wrong");
            }
        }
    }

}

function reset() {
    let xhr = new XMLHttpRequest();
    xhr.open("POST", "/reset", true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(JSON.stringify({conversation_id: "1234567890abcdef"}));

    xhr.onload = function() {
        let response = JSON.parse(this.responseText);
        console.log(response);

        if (response.hasOwnProperty('ok') && response['ok']) {
            location.reload();
        }
    }
}

document.getElementById('chat-input').addEventListener('keyup', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});
