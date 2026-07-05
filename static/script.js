const errorBanner = document.getElementById('error-banner');

function showError(message) {
    errorBanner.textContent = message;
    errorBanner.classList.remove('hidden');
    setTimeout(() => errorBanner.classList.add('hidden'), 5000);
}

// Handle Upload
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('pdf-file');
    const btn = document.getElementById('upload-btn');
    const statusText = document.getElementById('upload-status');
    
    if (!fileInput.files[0]) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    btn.disabled = true;
    btn.textContent = 'Uploading...';

    try {
        const response = await fetch('/upload', { method: 'POST', body: formData });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || 'Upload failed');

        document.getElementById('doc-id').value = data.doc_id;
        statusText.textContent = `✓ Document Ready`;
        statusText.classList.remove('hidden');
        document.getElementById('query-section').classList.remove('hidden');
        fileInput.value = ''; 
    } catch (error) {
        showError(error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Upload PDF';
    }
});

// Handle Query (Streaming)
document.getElementById('query-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const docId = document.getElementById('doc-id').value;
    const question = document.getElementById('question').value;
    const btn = document.getElementById('query-btn');
    const responseSection = document.getElementById('response-section');
    const answerText = document.getElementById('answer-text');
    const sourcesContainer = document.getElementById('sources-container');

    btn.disabled = true;
    btn.textContent = 'Thinking...';
    responseSection.classList.remove('hidden');
    
    answerText.textContent = '';
    sourcesContainer.innerHTML = '';

    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doc_id: docId, question: question })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Query failed');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); 
            
            for (const line of lines) {
                if (line.trim()) {
                    const data = JSON.parse(line);
                    
                    if (data.error) showError(data.error);
                    
                    if (data.sources) {
                        data.sources.forEach((source) => {
                            const div = document.createElement('div');
                            div.className = 'source-box';
                            // Remove the "Chunk X:" text and format it as a clean quote
                            div.textContent = `"...${source.substring(0, 150).trim()}..."`;
                            sourcesContainer.appendChild(div);
                        });
                    }
                    
                    if (data.text) {
                        answerText.textContent += data.text;
                    }
                }
            }
        }
    } catch (error) {
        showError(error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Ask Question';
    }
});