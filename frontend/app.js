const API_BASE = "/api/v1";

// DOM Elements
const layer1 = document.getElementById("layer1");
const layer2 = document.getElementById("layer2");
const fileInput = document.getElementById("damage-upload");
const fileNameDisplay = document.getElementById("file-name");
const submitLayer1Btn = document.getElementById("submit-layer1");
const loader = document.getElementById("loader");
const successMessage = document.getElementById("success-message");
const successText = document.getElementById("success-text");

const dynamicCodeDisplay = document.getElementById("dynamic-code");
const timeLeftDisplay = document.getElementById("time-left");
const captureBtn = document.getElementById("capture-btn");
const tryAgainBtn = document.getElementById("try-again-btn");
const video = document.getElementById("webcam");
const canvas = document.getElementById("canvas");

// State
let currentSessionId = null;
let timerInterval = null;
let expireTimestamp = 0;
let stream = null;

// Extracted from URL (passed from Clarification Layer)
const urlParams = new URLSearchParams(window.location.search);
const orderId = urlParams.get('order_id');
const returnReason = urlParams.get('reason') || "Not Specified";
const returnComments = urlParams.get('comments') || "";

if (!orderId) {
    alert("No order_id provided. Redirecting to Orders.");
    window.location.href = "orders.html";
}

// --- Layer 1 Logic ---

fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        fileNameDisplay.textContent = e.target.files[0].name;
        submitLayer1Btn.style.display = "block";
    }
});

async function compressImageKeepExif(file) {
    return new Promise((resolve) => {
        // If not a JPEG, just return the file as is (can't easily manipulate EXIF without huge libs)
        if (file.type !== "image/jpeg" && file.type !== "image/jpg") {
            resolve(file);
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const dataURL = e.target.result;
            
            // 1. Extract original EXIF
            let originalExifObj = null;
            try {
                originalExifObj = piexif.load(dataURL);
            } catch (err) {
                console.log("No EXIF found");
            }
            
            // 2. Load into Image to resize
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement("canvas");
                const MAX_WIDTH = 1000;
                let width = img.width;
                let height = img.height;
                
                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }
                
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, width, height);
                
                // 3. Get compressed JPEG
                let jpegUrl = canvas.toDataURL("image/jpeg", 0.7);
                
                // 4. Re-inject EXIF
                if (originalExifObj) {
                    try {
                        const exifStr = piexif.dump(originalExifObj);
                        jpegUrl = piexif.insert(exifStr, jpegUrl);
                    } catch (e) {
                        console.error("Failed to re-inject EXIF", e);
                    }
                }
                
                fetch(jpegUrl).then(res => res.blob()).then(blob => {
                    resolve(new File([blob], file.name, { type: "image/jpeg" }));
                });
            };
            img.src = dataURL;
        };
        reader.readAsDataURL(file);
    });
}

submitLayer1Btn.addEventListener("click", async () => {
    if (fileInput.files.length === 0) return;
    
    loader.style.display = "block";
    layer1.style.display = "none";
    
    // Do NOT compress the image client-side for Layer 1.
    // We MUST upload the raw, pristine image file to guarantee that complex hardware EXIF 
    // tags (like Aperture and Shutter Speed in the Exif IFD) are not corrupted by JS libraries.
    const rawFile = fileInput.files[0];
    
    const formData = new FormData();
    formData.append("file", rawFile);
    formData.append("order_id", orderId);
    formData.append("reason", returnReason);
    formData.append("comments", returnComments);
    
    try {
        const response = await fetch(`${API_BASE}/analyze-layer1`, {
            method: "POST",
            headers: { "Bypass-Tunnel-Reminder": "true" },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "approved") {
            showSuccess(data.message);
        } else if (response.status === 403) {
            alert("Verification Failed: " + (data.detail || "Item does not match."));
            layer1.style.display = "block";
        } else if (data.status === "challenge_required") {
            // Trap triggered
            initLayer2(data.session_id, data.code, data.timeout);
        } else {
            alert("Unexpected error: " + (data.detail || "Unknown error"));
            layer1.style.display = "block";
        }
    } catch (err) {
        alert("Failed to connect to API");
        layer1.style.display = "block";
    } finally {
        loader.style.display = "none";
    }
});

// --- Layer 2 Logic ---

async function initLayer2(sessionId, code, timeoutSeconds) {
    layer1.style.display = "none";
    layer2.style.display = "block";
    
    currentSessionId = sessionId;
    dynamicCodeDisplay.textContent = code;
    expireTimestamp = Date.now() + (timeoutSeconds * 1000);
    
    startTimer();
    await startWebcam();
}

async function startWebcam() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        video.srcObject = stream;
    } catch (err) {
        console.error("Camera error:", err);
        alert("Camera access is required for this step. Please allow camera permissions.");
    }
}

function stopWebcam() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
}

function startTimer() {
    clearInterval(timerInterval);
    captureBtn.disabled = false;
    captureBtn.style.display = "block";
    tryAgainBtn.style.display = "none";
    
    timerInterval = setInterval(() => {
        const now = Date.now();
        const remaining = Math.max(0, Math.floor((expireTimestamp - now) / 1000));
        
        timeLeftDisplay.textContent = remaining;
        
        if (remaining <= 0) {
            clearInterval(timerInterval);
            captureBtn.disabled = true;
            captureBtn.style.display = "none";
            tryAgainBtn.style.display = "block";
            timeLeftDisplay.textContent = "0";
        }
    }, 1000);
}

tryAgainBtn.addEventListener("click", async () => {
    loader.style.display = "block";
    layer2.style.display = "none";
    try {
        const response = await fetch(`${API_BASE}/refresh-session/${currentSessionId}`, {
            headers: { "Bypass-Tunnel-Reminder": "true" }
        });
        const data = await response.json();
        
        if (response.ok) {
            dynamicCodeDisplay.textContent = data.code;
            expireTimestamp = Date.now() + (data.timeout * 1000);
            layer2.style.display = "block";
            startTimer();
        } else {
            alert("Failed to refresh session.");
            layer2.style.display = "block";
        }
    } catch (err) {
        alert("Connection error.");
        layer2.style.display = "block";
    } finally {
        loader.style.display = "none";
    }
});

captureBtn.addEventListener("click", async () => {
    // 1. Draw video to canvas and compress for speed
    const MAX_WIDTH = 1000;
    let width = video.videoWidth;
    let height = video.videoHeight;
    if (width > MAX_WIDTH) {
        height *= MAX_WIDTH / width;
        width = MAX_WIDTH;
    }
    
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // 2. Get JPEG base64 from canvas (0.7 quality to reduce time lag)
    const jpegDataUrl = canvas.toDataURL("image/jpeg", 0.7);
    
    // 3. Inject EXIF using piexifjs
    let exifObj = {"0th": {}};
    // 305 is the tag for Software
    exifObj["0th"][piexif.ImageIFD.Software] = "Mock_Native_Camera";
    const exifStr = piexif.dump(exifObj);
    const finalJpegDataUrl = piexif.insert(exifStr, jpegDataUrl);
    
    // 4. Convert DataURL to Blob
    const res = await fetch(finalJpegDataUrl);
    const blob = await res.blob();
    
    // 5. Send to Layer 2 API
    const formData = new FormData();
    formData.append("file", blob, "capture.jpg");
    formData.append("session_id", currentSessionId);
    
    layer2.style.display = "none";
    loader.style.display = "block";
    loader.textContent = "Analyzing image with Gemini Vision AI. Please wait...";
    
    try {
        const response = await fetch(`${API_BASE}/analyze-layer2`, {
            method: "POST",
            headers: { "Bypass-Tunnel-Reminder": "true" },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "approved") {
            stopWebcam();
            showSuccess(data.message);
        } else {
            alert("Verification Failed:\n" + (data.detail || "Unknown error"));
            layer2.style.display = "block";
        }
    } catch (err) {
        alert("Failed to submit.");
        layer2.style.display = "block";
    } finally {
        loader.style.display = "none";
        loader.textContent = "Processing your request...";
    }
});

function showSuccess(msg) {
    layer1.style.display = "none";
    layer2.style.display = "none";
    successMessage.style.display = "block";
    successText.textContent = msg;
}
