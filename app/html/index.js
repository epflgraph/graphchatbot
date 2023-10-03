function appendMessage(className, message) {
    const chatContainer = document.getElementById('chat-container');
    const messageElem = document.createElement('div');

    messageElem.className = className;
    messageElem.innerText = message;

    chatContainer.appendChild(messageElem);
    chatContainer.scrollTop = chatContainer.scrollHeight;  // Auto scroll to bottom
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
        xhr.send(JSON.stringify({conversation_id: "1234567890abcdef", text: message}));

        xhr.onload = function() {
            try {
                // Extract response fields
                let response = JSON.parse(this.responseText)
                let nodeset = response["nodeset"];
                let context = response["context"];
                let context_message = response["context_message"].trim();

                console.log(context);

                // Convert object to string
                let message = nodeset.map((node) => `[${node['NodeType']}] ${node['Title']} (${node['NodeKey']})`).join('\n');

                if (context_message !== '') {
                    appendMessage('context-message', context_message);
                }

                if (message !== '') {
                    appendMessage('bot-message', message);
                } else {
                    appendMessage('bot-message', "<No results>");
                }
            } catch (error) {
                appendMessage('bot-message', "<Something went wrong>");
            }
        }
    }

}

document.getElementById('chat-input').addEventListener('keyup', function(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});