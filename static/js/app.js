/**
 * TubeDrop Studio — Main Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // State
    const state = {
        currentFilter: 'all',
        currentSort: 'newest',
        searchQuery: '',
        activeTasks: new Map(),
        pollingInterval: null,
        currentPreviewData: null,
        deleteTargetId: null,
        selectedLocalFile: null
    };

    // DOM Elements
    const elements = {
        // Stats
        statVideosCount: document.getElementById('stat-videos-count'),
        statStorageSize: document.getElementById('stat-storage-size'),
        filterAllCount: document.getElementById('filter-all-count'),
        filterYtCount: document.getElementById('filter-yt-count'),
        filterUploadCount: document.getElementById('filter-upload-count'),

        // Ingest Tabs
        tabBtns: document.querySelectorAll('.tab-btn'),
        tabContents: document.querySelectorAll('.tab-content'),

        // YouTube Ingest
        ytUrlInput: document.getElementById('youtube-url-input'),
        btnPaste: document.getElementById('btn-paste-clipboard'),
        btnInspect: document.getElementById('btn-inspect-url'),
        ytPreviewBox: document.getElementById('yt-preview-box'),
        previewThumb: document.getElementById('preview-thumb'),
        previewDuration: document.getElementById('preview-duration'),
        previewTitle: document.getElementById('preview-title'),
        previewChannel: document.getElementById('preview-channel'),
        previewViews: document.getElementById('preview-views'),
        selectQuality: document.getElementById('select-quality'),
        customTitleInput: document.getElementById('custom-title-input'),
        btnConfirmImport: document.getElementById('btn-confirm-import'),
        btnCancelPreview: document.getElementById('btn-cancel-preview'),
        btnOpenEmbed: document.getElementById('btn-open-embed'),

        // Local Upload
        dropzone: document.getElementById('upload-dropzone'),
        localFileInput: document.getElementById('local-file-input'),
        btnBrowseFiles: document.getElementById('btn-browse-files'),
        localUploadForm: document.getElementById('local-upload-form'),
        selectedFileName: document.getElementById('selected-file-name'),
        selectedFileSize: document.getElementById('selected-file-size'),
        btnRemoveFile: document.getElementById('btn-remove-selected-file'),
        localTitleInput: document.getElementById('local-title-input'),
        btnStartUpload: document.getElementById('btn-start-upload'),
        btnCancelUpload: document.getElementById('btn-cancel-upload'),

        // Tasks
        tasksSection: document.getElementById('tasks-section'),
        tasksContainer: document.getElementById('tasks-container'),
        tasksCountBadge: document.getElementById('tasks-count-badge'),

        // Library
        searchInput: document.getElementById('search-input'),
        searchClearBtn: document.getElementById('search-clear-btn'),
        filterPills: document.querySelectorAll('.filter-pill'),
        sortSelect: document.getElementById('sort-select'),
        videoGrid: document.getElementById('video-grid'),
        emptyState: document.getElementById('empty-state'),
        btnRefresh: document.getElementById('btn-refresh-library'),

        // Modals
        playerModal: document.getElementById('player-modal'),
        studioVideo: document.getElementById('studio-video'),
        playerVideoTitle: document.getElementById('player-video-title'),
        playerSourceBadge: document.getElementById('player-source-badge'),
        playerChannelInfo: document.getElementById('player-channel-info'),
        playerFormatInfo: document.getElementById('player-format-info'),
        playerSizeInfo: document.getElementById('player-size-info'),
        playerDurationInfo: document.getElementById('player-duration-info'),
        playerDownloadBtn: document.getElementById('player-download-btn'),
        playerCopyLinkBtn: document.getElementById('player-copy-link-btn'),
        btnClosePlayer: document.getElementById('btn-close-player'),

        embedModal: document.getElementById('embed-preview-modal'),
        embedIframe: document.getElementById('embed-iframe'),
        embedTitle: document.getElementById('embed-video-title'),
        btnCloseEmbed: document.getElementById('btn-close-embed'),

        deleteModal: document.getElementById('delete-modal'),
        deleteTargetTitle: document.getElementById('delete-target-title'),
        btnConfirmDelete: document.getElementById('btn-confirm-delete'),
        btnCancelDelete: document.getElementById('btn-cancel-delete'),
        btnCloseDelete: document.getElementById('btn-close-delete'),

        toastContainer: document.getElementById('toast-container')
    };

    // Helpers & Utilities
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle-2';
        if (type === 'error') iconName = 'alert-circle';

        toast.innerHTML = `
            <div class="toast-icon"><i data-lucide="${iconName}"></i></div>
            <div class="toast-message">${escapeHtml(message)}</div>
        `;
        elements.toastContainer.appendChild(toast);
        if (window.lucide) lucide.createIcons({ root: toast });

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 250);
        }, 4000);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatNumber(num) {
        if (!num) return '0';
        if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toLocaleString();
    }

    function formatBytes(bytes) {
        if (!bytes || bytes <= 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Tab Switching
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            elements.tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const target = btn.getAttribute('data-tab');
            document.getElementById(target).classList.add('active');
        });
    });

    // YouTube Inspection
    elements.btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                elements.ytUrlInput.value = text.trim();
                showToast('Link pasted from clipboard', 'info');
                inspectYouTubeUrl();
            }
        } catch (err) {
            elements.ytUrlInput.focus();
            showToast('Please press Ctrl+V to paste into the box', 'info');
        }
    });

    elements.ytUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            inspectYouTubeUrl();
        }
    });

    elements.btnInspect.addEventListener('click', () => {
        inspectYouTubeUrl();
    });

    async function inspectYouTubeUrl() {
        const url = elements.ytUrlInput.value.trim();
        if (!url) {
            showToast('Please enter a YouTube video URL', 'error');
            elements.ytUrlInput.focus();
            return;
        }

        const btn = elements.btnInspect;
        const btnText = btn.querySelector('.btn-text');
        const spinner = btn.querySelector('.spinner-small');
        const arrow = btn.querySelector('[data-lucide="arrow-right"]');

        btnText.textContent = 'Inspecting...';
        if (spinner) spinner.style.display = 'inline-block';
        if (arrow) arrow.style.display = 'none';
        btn.disabled = true;

        try {
            const res = await fetch('/api/youtube/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const result = await res.json();

            if (!result.success) {
                throw new Error(result.error || 'Failed to inspect video');
            }

            renderPreview(result.data, url);
        } catch (err) {
            showToast(err.message, 'error');
            elements.ytPreviewBox.style.display = 'none';
        } finally {
            btnText.textContent = 'Inspect & Preview';
            if (spinner) spinner.style.display = 'none';
            if (arrow) arrow.style.display = 'inline-block';
            btn.disabled = false;
        }
    }

    function renderPreview(data, sourceUrl) {
        state.currentPreviewData = { ...data, sourceUrl };

        elements.previewThumb.src = data.thumbnail || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=640';
        elements.previewDuration.textContent = data.duration_str || '00:00';
        elements.previewTitle.textContent = data.title || 'Untitled';
        elements.previewChannel.textContent = data.channel || 'Unknown Channel';
        elements.previewViews.textContent = `${formatNumber(data.views_count)} views`;
        elements.customTitleInput.value = data.title || '';

        elements.selectQuality.innerHTML = '';
        (data.qualities || []).forEach(q => {
            const opt = document.createElement('option');
            opt.value = q.id;
            opt.textContent = q.label;
            elements.selectQuality.appendChild(opt);
        });

        elements.ytPreviewBox.style.display = 'block';
        if (window.lucide) lucide.createIcons({ root: elements.ytPreviewBox });
    }

    elements.btnCancelPreview.addEventListener('click', () => {
        elements.ytPreviewBox.style.display = 'none';
        state.currentPreviewData = null;
    });

    elements.btnOpenEmbed.addEventListener('click', () => {
        if (!state.currentPreviewData || !state.currentPreviewData.id) return;
        const videoId = state.currentPreviewData.id;
        elements.embedTitle.textContent = state.currentPreviewData.title;
        elements.embedIframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
        elements.embedModal.style.display = 'flex';
    });

    elements.btnCloseEmbed.addEventListener('click', () => {
        elements.embedModal.style.display = 'none';
        elements.embedIframe.src = '';
    });

    // Import YouTube to Library
    elements.btnConfirmImport.addEventListener('click', async () => {
        if (!state.currentPreviewData) return;

        const url = state.currentPreviewData.sourceUrl;
        const quality = elements.selectQuality.value || 'best';
        const customTitle = elements.customTitleInput.value.trim() || state.currentPreviewData.title;

        elements.btnConfirmImport.disabled = true;

        try {
            const res = await fetch('/api/youtube/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url,
                    quality,
                    custom_title: customTitle
                })
            });
            const result = await res.json();

            if (!result.success) {
                throw new Error(result.error || 'Failed to start import');
            }

            showToast('Download started in background!', 'success');
            elements.ytPreviewBox.style.display = 'none';
            elements.ytUrlInput.value = '';
            state.currentPreviewData = null;

            startTaskTracking(result.task_id);
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            elements.btnConfirmImport.disabled = false;
        }
    });

    // Local File Upload
    elements.btnBrowseFiles.addEventListener('click', () => {
        elements.localFileInput.click();
    });

    elements.dropzone.addEventListener('click', (e) => {
        if (e.target !== elements.btnBrowseFiles && !elements.btnBrowseFiles.contains(e.target)) {
            elements.localFileInput.click();
        }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        elements.dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            elements.dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        elements.dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            elements.dropzone.classList.remove('dragover');
        });
    });

    elements.dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleLocalFileSelection(files[0]);
        }
    });

    elements.localFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleLocalFileSelection(e.target.files[0]);
        }
    });

    function handleLocalFileSelection(file) {
        state.selectedLocalFile = file;
        elements.selectedFileName.textContent = file.name;
        elements.selectedFileSize.textContent = formatBytes(file.size);
        elements.localTitleInput.value = file.name.replace(/\.[^/.]+$/, "");
        elements.dropzone.style.display = 'none';
        elements.localUploadForm.style.display = 'block';
        if (window.lucide) lucide.createIcons({ root: elements.localUploadForm });
    }

    elements.btnRemoveFile.addEventListener('click', resetLocalUpload);
    elements.btnCancelUpload.addEventListener('click', resetLocalUpload);

    function resetLocalUpload() {
        state.selectedLocalFile = null;
        elements.localFileInput.value = '';
        elements.dropzone.style.display = 'block';
        elements.localUploadForm.style.display = 'none';
    }

    elements.btnStartUpload.addEventListener('click', async () => {
        if (!state.selectedLocalFile) return;

        const file = state.selectedLocalFile;
        const title = elements.localTitleInput.value.trim() || file.name;

        const formData = new FormData();
        formData.append('video_file', file);
        formData.append('custom_title', title);

        elements.btnStartUpload.disabled = true;
        elements.btnStartUpload.innerHTML = '<div class="spinner-small"></div><span>Uploading...</span>';

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const result = await res.json();

            if (!result.success) {
                throw new Error(result.error || 'Upload failed');
            }

            showToast('Video uploaded successfully!', 'success');
            resetLocalUpload();
            loadLibrary();
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            elements.btnStartUpload.disabled = false;
            elements.btnStartUpload.innerHTML = '<i data-lucide="upload"></i><span>Upload Video</span>';
            if (window.lucide) lucide.createIcons({ root: elements.btnStartUpload });
        }
    });

    // Task Tracking & Polling Engine
    function startTaskTracking(taskId) {
        state.activeTasks.set(taskId, true);
        elements.tasksSection.style.display = 'block';
        pollTasks();

        if (!state.pollingInterval) {
            state.pollingInterval = setInterval(pollTasks, 1500);
        }
    }

    async function pollTasks() {
        try {
            const res = await fetch('/api/tasks');
            const data = await res.json();
            if (!data.success) return;

            const tasks = data.tasks || [];
            renderTasks(tasks);

            const hasRunning = tasks.some(t => ['queued', 'starting', 'fetching', 'downloading', 'processing'].includes(t.status));
            if (!hasRunning) {
                if (state.pollingInterval) {
                    clearInterval(state.pollingInterval);
                    state.pollingInterval = null;
                }
            }
        } catch (err) {
            console.error('Error polling tasks:', err);
        }
    }

    function renderTasks(tasks) {
        if (!tasks || tasks.length === 0) {
            elements.tasksSection.style.display = 'none';
            return;
        }

        elements.tasksSection.style.display = 'block';
        const activeCount = tasks.filter(t => !['completed', 'error'].includes(t.status)).length;
        elements.tasksCountBadge.textContent = `${activeCount} active`;

        elements.tasksContainer.innerHTML = '';

        tasks.forEach(task => {
            const card = document.createElement('div');
            card.className = 'task-card';

            const isCompleted = task.status === 'completed';
            const isError = task.status === 'error';
            const progress = Math.min(100, Math.max(0, task.progress || 0));

            let statusClass = `task-status-${task.status}`;
            let statusLabel = task.status;
            if (task.status === 'downloading') statusLabel = `Downloading ${progress.toFixed(0)}%`;
            if (task.status === 'processing') statusLabel = 'Processing with FFmpeg';
            if (task.status === 'completed') statusLabel = 'Complete';
            if (task.status === 'error') statusLabel = 'Failed';

            card.innerHTML = `
                <div class="task-top-row">
                    <div class="task-title-wrap">
                        <i data-lucide="${isCompleted ? 'check-circle' : isError ? 'alert-triangle' : 'loader'}" 
                           class="${!isCompleted && !isError ? 'pulse-icon' : ''}"></i>
                        <span class="task-title" title="${escapeHtml(task.title)}">${escapeHtml(task.title)}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="task-status-badge ${statusClass}">${statusLabel}</span>
                        ${isCompleted && task.video_id ? `
                            <button class="btn btn-sm btn-primary" onclick="window.playVideoById(${task.video_id})" style="padding: 4px 10px; font-size: 0.75rem;">
                                <i data-lucide="play"></i> Watch
                            </button>
                        ` : ''}
                        ${(isCompleted || isError) ? `
                            <button class="btn-icon" title="Dismiss" onclick="window.dismissTask('${task.task_id}')" style="width: 26px; height: 26px;">
                                <i data-lucide="x" style="width: 14px; height: 14px;"></i>
                            </button>
                        ` : ''}
                    </div>
                </div>

                <div class="progress-bar-container">
                    <div class="progress-bar-fill ${isCompleted ? 'completed' : ''}" style="width: ${progress}%"></div>
                </div>

                <div class="task-metrics-row">
                    <span class="task-status-text">${escapeHtml(task.status_text || '')}</span>
                    <span class="task-stats-numbers">
                        ${task.speed_str && task.speed_str !== '--' ? `<span>Speed: ${task.speed_str}</span> &bull; ` : ''}
                        ${task.eta_str && task.eta_str !== '--' ? `<span>ETA: ${task.eta_str}</span> &bull; ` : ''}
                        <span>${progress.toFixed(0)}%</span>
                    </span>
                </div>
            `;

            elements.tasksContainer.appendChild(card);
        });

        if (window.lucide) lucide.createIcons({ root: elements.tasksContainer });

        const justCompleted = tasks.some(t => t.status === 'completed' && !t.notified);
        if (justCompleted) {
            loadLibrary();
        }
    }

    window.dismissTask = async function(taskId) {
        try {
            await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
            pollTasks();
        } catch (err) {
            console.error('Error dismissing task:', err);
        }
    };

    // Library & Video Gallery
    async function loadLibrary() {
        const params = new URLSearchParams({
            filter: state.currentFilter,
            sort: state.currentSort,
            q: state.searchQuery
        });

        try {
            const res = await fetch(`/api/videos?${params.toString()}`);
            const data = await res.json();
            if (!data.success) throw new Error(data.error);

            renderLibrary(data.videos || []);
            updateStats(data.stats || {});
        } catch (err) {
            console.error('Failed to load library:', err);
            showToast('Failed to load media vault', 'error');
        }
    }

    function updateStats(stats) {
        elements.statVideosCount.textContent = `${stats.total_videos || 0} videos`;
        elements.statStorageSize.textContent = stats.total_bytes_str || '0 B';

        elements.filterAllCount.textContent = stats.total_videos || 0;
        elements.filterYtCount.textContent = stats.yt_count || 0;
        elements.filterUploadCount.textContent = stats.upload_count || 0;
    }

    function renderLibrary(videos) {
        elements.videoGrid.innerHTML = '';

        if (!videos || videos.length === 0) {
            elements.videoGrid.style.display = 'none';
            elements.emptyState.style.display = 'block';
            if (window.lucide) lucide.createIcons({ root: elements.emptyState });
            return;
        }

        elements.videoGrid.style.display = 'grid';
        elements.emptyState.style.display = 'none';

        videos.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';

            const isYouTube = video.source_type === 'youtube';
            const thumbSrc = video.thumbnail_path ? `/static/${video.thumbnail_path}` : null;

            card.innerHTML = `
                <div class="video-thumb-wrap" onclick="window.playVideoById(${video.id})">
                    ${thumbSrc ? `
                        <img src="${thumbSrc}" alt="${escapeHtml(video.title)}" class="video-thumb-img" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                        <div class="video-thumb-placeholder" style="display: none;"><i data-lucide="play-circle"></i></div>
                    ` : `
                        <div class="video-thumb-placeholder"><i data-lucide="play-circle"></i></div>
                    `}
                    <span class="video-duration">${escapeHtml(video.duration_str || '00:00')}</span>
                    <span class="video-source-badge ${isYouTube ? 'yt' : 'upload'}">
                        <i data-lucide="${isYouTube ? 'youtube' : 'upload-cloud'}"></i>
                        <span>${isYouTube ? 'YouTube' : 'Upload'}</span>
                    </span>
                    <div class="play-hover-overlay">
                        <div class="play-bubble">
                            <i data-lucide="play"></i>
                        </div>
                    </div>
                </div>

                <div class="video-body">
                    <div>
                        <h4 class="video-title" title="${escapeHtml(video.title)}">${escapeHtml(video.title)}</h4>
                        <p class="video-channel">${escapeHtml(video.channel || 'Studio')}</p>
                    </div>

                    <div>
                        <div class="video-meta-row">
                            <span class="format-tag">${escapeHtml(video.format_name || 'MP4')}</span>
                            <span>${escapeHtml(video.file_size_str || '0 B')}</span>
                            <span>${video.created_at ? video.created_at.split(' ')[0] : ''}</span>
                        </div>

                        <div class="video-card-actions">
                            <button class="btn-card-action primary" onclick="window.playVideoById(${video.id})" title="Play video">
                                <i data-lucide="play"></i> Play
                            </button>
                            <a href="/api/videos/${video.id}/download" class="btn-card-action" title="Download to device">
                                <i data-lucide="download"></i> Save
                            </a>
                            <button class="btn-card-action" onclick="window.copyVideoLink(${video.id})" title="Copy Stream Link">
                                <i data-lucide="link-2"></i>
                            </button>
                            <button class="btn-card-action danger" onclick="window.confirmDeleteVideo(${video.id}, '${escapeHtml(video.title)}')" title="Delete">
                                <i data-lucide="trash-2"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;

            elements.videoGrid.appendChild(card);
        });

        if (window.lucide) lucide.createIcons({ root: elements.videoGrid });
    }

    // Filter Pills
    elements.filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            elements.filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            state.currentFilter = pill.getAttribute('data-filter');
            loadLibrary();
        });
    });

    // Sort Select
    elements.sortSelect.addEventListener('change', (e) => {
        state.currentSort = e.target.value;
        loadLibrary();
    });

    // Search Input with Debounce
    let searchDebounceTimer = null;
    elements.searchInput.addEventListener('input', (e) => {
        const val = e.target.value;
        elements.searchClearBtn.style.display = val ? 'flex' : 'none';

        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            state.searchQuery = val;
            loadLibrary();
        }, 300);
    });

    elements.searchClearBtn.addEventListener('click', () => {
        elements.searchInput.value = '';
        elements.searchClearBtn.style.display = 'none';
        state.searchQuery = '';
        loadLibrary();
    });

    elements.btnRefresh.addEventListener('click', () => {
        loadLibrary();
        pollTasks();
        showToast('Media vault refreshed', 'info');
    });

    // Video Player Modal
    window.playVideoById = async function(id) {
        try {
            const res = await fetch(`/api/videos/${id}`);
            const data = await res.json();
            if (!data.success) throw new Error(data.error);

            const video = data.video;
            elements.playerVideoTitle.textContent = video.title;
            elements.playerSourceBadge.textContent = video.source_type === 'youtube' ? 'YouTube Import' : 'Local Upload';
            elements.playerChannelInfo.innerHTML = `<i data-lucide="user"></i> ${escapeHtml(video.channel || 'Studio')}`;
            elements.playerFormatInfo.innerHTML = `<i data-lucide="file-video"></i> ${escapeHtml(video.format_name || 'MP4')}`;
            elements.playerSizeInfo.innerHTML = `<i data-lucide="database"></i> ${video.file_size_str}`;
            elements.playerDurationInfo.innerHTML = `<i data-lucide="clock"></i> ${video.duration_str}`;

            elements.playerDownloadBtn.href = `/api/videos/${video.id}/download`;
            elements.playerDownloadBtn.download = video.file_name;

            elements.playerCopyLinkBtn.onclick = () => {
                const streamUrl = `${window.location.origin}/api/videos/${video.id}/stream`;
                navigator.clipboard.writeText(streamUrl);
                showToast('Stream link copied to clipboard!', 'success');
            };

            if (video.thumbnail_path) {
                elements.studioVideo.poster = `/static/${video.thumbnail_path}`;
            } else {
                elements.studioVideo.removeAttribute('poster');
            }

            elements.studioVideo.src = `/api/videos/${video.id}/stream`;
            elements.playerModal.style.display = 'flex';
            elements.studioVideo.play().catch(() => {});

            if (window.lucide) lucide.createIcons({ root: elements.playerModal });
        } catch (err) {
            showToast('Unable to load video: ' + err.message, 'error');
        }
    };

    function closePlayer() {
        elements.studioVideo.pause();
        elements.studioVideo.src = '';
        elements.playerModal.style.display = 'none';
    }

    elements.btnClosePlayer.addEventListener('click', closePlayer);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closePlayer();
            elements.embedModal.style.display = 'none';
            elements.embedIframe.src = '';
            elements.deleteModal.style.display = 'none';
        }
    });

    window.copyVideoLink = function(id) {
        const streamUrl = `${window.location.origin}/api/videos/${id}/stream`;
        navigator.clipboard.writeText(streamUrl);
        showToast('Stream URL copied to clipboard!', 'success');
    };

    // Delete Confirmation
    window.confirmDeleteVideo = function(id, title) {
        state.deleteTargetId = id;
        elements.deleteTargetTitle.textContent = `"${title}"`;
        elements.deleteModal.style.display = 'flex';
        if (window.lucide) lucide.createIcons({ root: elements.deleteModal });
    };

    function closeDeleteModal() {
        state.deleteTargetId = null;
        elements.deleteModal.style.display = 'none';
    }

    elements.btnCancelDelete.addEventListener('click', closeDeleteModal);
    elements.btnCloseDelete.addEventListener('click', closeDeleteModal);

    elements.btnConfirmDelete.addEventListener('click', async () => {
        if (!state.deleteTargetId) return;

        try {
            const res = await fetch(`/api/videos/${state.deleteTargetId}`, { method: 'DELETE' });
            const data = await res.json();
            if (!data.success) throw new Error(data.error);

            showToast('Video deleted from vault', 'info');
            closeDeleteModal();
            loadLibrary();
        } catch (err) {
            showToast('Failed to delete video: ' + err.message, 'error');
        }
    });

    // Close modals on clicking backdrop
    [elements.playerModal, elements.embedModal, elements.deleteModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                if (modal === elements.playerModal) closePlayer();
                if (modal === elements.embedModal) {
                    elements.embedModal.style.display = 'none';
                    elements.embedIframe.src = '';
                }
                if (modal === elements.deleteModal) closeDeleteModal();
            }
        });
    });

    // Initial load
    loadLibrary();
    pollTasks();
});
