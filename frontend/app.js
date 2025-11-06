// Frontend JavaScript for RAG Chatbot

const API_BASE_URL = 'http://localhost:8000';
let sessionId = null;
let selectedDocuments = new Set();
let conversationId = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // Get session ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    sessionId = urlParams.get('session_id');
    
    // Check if authenticated
    if (sessionId) {
        showApp();
        loadDocuments();
        loadKnowledgeBase();
        enableChat();
    } else {
        showAuth();
    }
    
    // Event listeners
    document.getElementById('signin-btn').addEventListener('click', signIn);
    document.getElementById('refresh-docs-btn').addEventListener('click', loadDocuments);
    document.getElementById('add-selected-btn').addEventListener('click', addToKnowledgeBase);
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    
    // Clear knowledge base button
    const clearKbBtn = document.getElementById('clear-kb-btn');
    if (clearKbBtn) {
        clearKbBtn.addEventListener('click', clearKnowledgeBase);
    }
    
    // Enter key in chat input
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});

function showAuth() {
    document.getElementById('auth-section').style.display = 'block';
    document.getElementById('app-section').style.display = 'none';
}

function showApp() {
    document.getElementById('auth-section').style.display = 'none';
    document.getElementById('app-section').style.display = 'block';
}

function signIn() {
    window.location.href = `${API_BASE_URL}/auth/login`;
}

async function loadDocuments() {
    const container = document.getElementById('documents-container');
    const loading = document.getElementById('documents-loading');
    
    loading.style.display = 'block';
    container.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/documents?session_id=${sessionId}`);
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.documents.length > 0) {
            data.documents.forEach(doc => {
                const docElement = createDocumentElement(doc);
                container.appendChild(docElement);
            });
        } else {
            container.innerHTML = '<p class="empty-state">No documents found.</p>';
        }
    } catch (error) {
        loading.style.display = 'none';
        container.innerHTML = `<p class="empty-state" style="color: red;">Error loading documents: ${error.message}</p>`;
    }
}

function createDocumentElement(doc) {
    const div = document.createElement('div');
    div.className = 'document-item';
    div.dataset.docId = doc.id;
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.dataset.docId = doc.id;
    checkbox.addEventListener('change', handleDocumentSelection);
    
    const info = document.createElement('div');
    info.className = 'document-info';
    
    const name = document.createElement('div');
    name.className = 'document-name';
    name.textContent = doc.name;
    
    const meta = document.createElement('div');
    meta.className = 'document-meta';
    const date = new Date(doc.modifiedTime).toLocaleDateString();
    meta.textContent = `Modified: ${date}`;
    
    info.appendChild(name);
    info.appendChild(meta);
    
    div.appendChild(checkbox);
    div.appendChild(info);
    
    return div;
}

function handleDocumentSelection(e) {
    const docId = e.target.dataset.docId;
    const docItem = e.target.closest('.document-item');
    
    if (e.target.checked) {
        selectedDocuments.add(docId);
        docItem.classList.add('selected');
    } else {
        selectedDocuments.delete(docId);
        docItem.classList.remove('selected');
    }
    
    updateSelectedCount();
    updateAddButton();
}

function updateSelectedCount() {
    const count = selectedDocuments.size;
    document.getElementById('selected-count').textContent = `${count} selected`;
}

function updateAddButton() {
    const btn = document.getElementById('add-selected-btn');
    btn.disabled = selectedDocuments.size === 0;
}

async function addToKnowledgeBase() {
    if (selectedDocuments.size === 0) return;
    
    const btn = document.getElementById('add-selected-btn');
    btn.disabled = true;
    btn.textContent = 'Adding...';
    
    console.log('Adding documents:', Array.from(selectedDocuments));
    
    try {
        // Clear knowledge base first to start fresh
        console.log('Clearing existing knowledge base...');
        await fetch(`${API_BASE_URL}/api/knowledge-base/clear`, {
            method: 'DELETE'
        });
        
        // Create AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout for large documents
        
        console.log('Sending request to:', `${API_BASE_URL}/api/knowledge-base/add?session_id=${sessionId}`);
        
        const response = await fetch(`${API_BASE_URL}/api/knowledge-base/add?session_id=${sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_ids: Array.from(selectedDocuments)
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            alert(`Successfully added ${data.added_count} document(s) to knowledge base!`);
            selectedDocuments.clear();
            
            // Clear selections in UI
            document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
                cb.closest('.document-item').classList.remove('selected');
            });
            
            updateSelectedCount();
            updateAddButton();
            loadKnowledgeBase();
            enableChat();
        } else {
            alert(`Error: ${data.message || 'Unknown error'}`);
            console.error('Add failed:', data);
        }
    } catch (error) {
        console.error('Exception adding documents:', error);
        if (error.name === 'AbortError') {
            alert('Request timed out. The document might be very large. Please try with a smaller document or wait longer.');
        } else {
            alert(`Error adding documents: ${error.message}`);
        }
    } finally {
        btn.disabled = false;
        btn.textContent = 'Add Selected to Knowledge Base';
    }
}

async function loadKnowledgeBase() {
    const container = document.getElementById('kb-container');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/knowledge-base/documents`);
        const data = await response.json();
        
        if (data.success && data.documents.length > 0) {
            container.innerHTML = data.documents.map(doc => 
                `<span class="kb-item">${doc.name}</span>`
            ).join('');
        } else {
            container.innerHTML = '<p class="empty-state">No documents in knowledge base yet.</p>';
        }
    } catch (error) {
        container.innerHTML = '<p class="empty-state" style="color: red;">Error loading knowledge base.</p>';
    }
}

async function clearKnowledgeBase() {
    if (!confirm('Are you sure you want to clear all documents from the knowledge base?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/knowledge-base/clear`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Knowledge base cleared successfully!');
            loadKnowledgeBase();
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (error) {
        alert(`Error clearing knowledge base: ${error.message}`);
    }
}

function enableChat() {
    document.getElementById('chat-input').disabled = false;
    document.getElementById('send-btn').disabled = false;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    
    if (!query) return;
    
    // Add user message to chat
    addMessageToChat('user', query);
    
    // Clear input
    input.value = '';
    input.disabled = true;
    document.getElementById('send-btn').disabled = true;
    
    // Show loading
    const loadingId = addMessageToChat('assistant', 'Thinking...', true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/chat?session_id=${sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                conversation_id: conversationId
            })
        });
        
        const data = await response.json();
        
        // Update conversation ID
        conversationId = data.conversation_id;
        
        // Remove loading message
        document.getElementById(loadingId)?.remove();
        
        // Add assistant response
        addMessageToChat('assistant', data.response, false, data.found_in_documents, data.sources);
        
    } catch (error) {
        document.getElementById(loadingId)?.remove();
        addMessageToChat('assistant', `Error: ${error.message}`, false);
    } finally {
        input.disabled = false;
        document.getElementById('send-btn').disabled = false;
        input.focus();
    }
}

function addMessageToChat(role, content, isLoading = false, foundInDocs = true, sources = []) {
    const container = document.getElementById('chat-container');
    
    // Remove welcome message if exists
    const welcomeMsg = container.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageId = 'msg-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${role}`;
    
    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = role === 'user' ? 'You' : 'Assistant';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    // Convert markdown-style bold (**text**) to HTML
    let formattedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert markdown-style italic (*text*) to HTML  
    formattedContent = formattedContent.replace(/\*(.*?)\*/g, '<em>$1</em>');
    contentDiv.innerHTML = formattedContent;
    
    messageDiv.appendChild(header);
    messageDiv.appendChild(contentDiv);
    
    if (!isLoading && role === 'assistant') {
        const footer = document.createElement('div');
        footer.className = 'message-footer';
        
        if (!foundInDocs) {
            const badge = document.createElement('span');
            badge.className = 'not-found-badge';
            badge.textContent = '⚠️ Answer not found in your documents';
            footer.appendChild(badge);
        }
        
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            sourcesDiv.innerHTML = '<strong>Sources:</strong> ';
            sources.forEach((source, index) => {
                const sourceSpan = document.createElement('span');
                sourceSpan.className = 'source-item';
                sourceSpan.textContent = source.document_name;
                sourcesDiv.appendChild(sourceSpan);
                // Add comma between sources (except last one)
                if (index < sources.length - 1) {
                    const comma = document.createTextNode(', ');
                    sourcesDiv.appendChild(comma);
                }
            });
            footer.appendChild(sourcesDiv);
        }
        
        messageDiv.appendChild(footer);
    }
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
    return messageId;
}

