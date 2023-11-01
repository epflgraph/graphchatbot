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
            link.innerText = dict[id]['Title'];
            link.target = 'blank_';
            messageElem.appendChild(link);
        } else {
            // Use a div to preserve text formatting and newlines
            const span = document.createElement('span');
            span.innerText = piece;
            messageElem.appendChild(span);
        }
    }

    chatContainer.appendChild(messageElem);
    chatContainer.scrollTop = chatContainer.scrollHeight;  // Auto scroll to bottom
}

function processResponseElem(elem, print_nodeset) {
    // Extract response fields
    let nodeset = elem["nodeset"];
    let context = elem["context"];
    let context_message = elem["context_message"].trim();

    // Print context message
    if (context_message !== '') {
        appendMessage('context-message', context_message);
    }

    if (print_nodeset) {
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

document.getElementById('chat-input').addEventListener('keyup', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});