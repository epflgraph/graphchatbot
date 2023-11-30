function parseLinks(text) {
    const markdownLinkRegex = /(\[.*?\])(\(.*?\))/gm;
    const subpieces = text.split(markdownLinkRegex);

    let elems = [];
    for (const subpiece of subpieces) {
        if (subpiece.startsWith('(') && subpiece.endsWith(')')) {
            // Skip URLs of Markdown links
            continue;
        }

        const index = subpieces.indexOf(subpiece);

        let nextSubpiece = "";
        if (index + 1 < subpieces.length) {
            nextSubpiece = subpieces[index + 1];
        }

        if (subpiece.startsWith('[') && subpiece.endsWith(']') && nextSubpiece) {
            // This subpiece is the link text of a markdown link
            let link = document.createElement('a');
            link.href = nextSubpiece.slice(1, -1);
            link.innerText = subpiece.slice(1, -1);
            link.target = 'blank_';
            elems.push(link);
        } else {
            // This segment is regular text
            const span = document.createElement('span');
            span.innerText = subpiece;
            elems.push(span);
        }
    }

    return elems;
}

function appendMessage(className, message, dict={}) {
    const chatContainer = document.getElementById('chat-container');
    const messageElem = document.createElement('div');

    messageElem.className = `message ${className}`;
    // messageElem.innerText = message;

    const pieces = message.split(/(%[^%$]+\$)/g);

    for (const piece of pieces) {
        if (piece.startsWith('%') && piece.endsWith('$')) {
            // Create an anchor element for the hyperlink
            const link = document.createElement('a');
            const id = piece.slice(1, -1);  // remove % and $
            const nodeType = dict[id]['NodeType'].toLowerCase();
            const nodeKey = dict[id]['NodeKey'];
            link.href = `https://graphsearch.epfl.ch/${nodeType}/${nodeKey}`;
            if (dict[id].hasOwnProperty('LinkText')) {
                link.innerText = dict[id]['LinkText'];
            } else {
                link.innerText = dict[id]['Title'];
            }
            link.target = 'blank_';
            messageElem.appendChild(link);
        } else {
            const elems = parseLinks(piece);
            for (elem of elems) {
                messageElem.appendChild(elem);
            }
        }
    }

    chatContainer.appendChild(messageElem);
    chatContainer.scrollTop = chatContainer.scrollHeight;  // Auto scroll to bottom
}

function processResponseElem(elem, print_nodeset) {
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

    // Print nodeset if needed
    if (print_nodeset && elem.hasOwnProperty('nodeset')) {
        let nodeset = elem["nodeset"];

        // Convert object to string
        let message = nodeset.map((node) => `[${node['NodeType']}] ${node['Title']} (${node['NodeKey']})`).join('\n');

        if (message !== '') {
            appendMessage('bot-message', message);
        } else {
            appendMessage('bot-message', "<No results>");
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

                if (response.hasOwnProperty('results') && response['results'].length > 0) {
                    if (response.hasOwnProperty('formatted_message') && response.hasOwnProperty('formatting_dict')) {
                        response['results'].forEach((elem) => processResponseElem(elem, false));
                        appendMessage('bot-message', response['formatted_message'], response['formatting_dict']);
                    }
                    else if (response.hasOwnProperty('message')) {
                        response['results'].forEach((elem) => processResponseElem(elem, false));
                        appendMessage('bot-message', response['message']);
                    } else {
                        response['results'].forEach((elem) => processResponseElem(elem, true));
                    }
                } else {
                    if (response.hasOwnProperty('message')) {
                        appendMessage('bot-message', response['message']);
                    } else {
                        appendMessage('error-message', "ERROR: Something went wrong");
                    }
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
