function appendMessage(className, message) {
    const chatContainer = document.getElementById('chat-container');
    const messageElem = document.createElement('div');

    messageElem.className = `message ${className}`;
    messageElem.innerText = message;

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
                    if (response.hasOwnProperty('message')) {
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