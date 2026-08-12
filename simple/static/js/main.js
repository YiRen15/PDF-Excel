document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const tabBtns = document.querySelectorAll('.tab-item');
    const uploadPanels = document.querySelectorAll('.tab-panel');
    
    const inputZip = document.getElementById('input-zip');
    const inputFiles = document.getElementById('input-files');
    const dropzoneZip = document.getElementById('dropzone-zip');
    const dropzoneFiles = document.getElementById('dropzone-files');
    const selectedZipBadge = document.getElementById('selected-zip-name');
    const selectedFilesBadge = document.getElementById('selected-files-count');
    
    const startParseBtn = document.getElementById('start-parse-btn');
    const resetBtn = document.getElementById('reset-btn');
    const downloadBtn = document.getElementById('download-btn');
    
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-bar-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressStatusText = document.getElementById('progress-status-text');
    const progressIconContainer = document.getElementById('progress-status-icon-container');
    
    const statsSection = document.getElementById('stats-section');
    const resultsCard = document.getElementById('results-card');
    const tableBody = document.getElementById('table-body');
    
    const searchInput = document.getElementById('search-input');
    const filterSelect = document.getElementById('filter-select');
    const pageSizeSelect = document.getElementById('page-size-select');
    const prevPageBtn = document.getElementById('prev-page-btn');
    const nextPageBtn = document.getElementById('next-page-btn');
    const currentPageNum = document.getElementById('current-page-num');
    const pageStart = document.getElementById('page-start');
    const pageEnd = document.getElementById('page-end');
    const pageTotal = document.getElementById('page-total');

    // Modal Elements
    const detailModal = document.getElementById('detail-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalOkBtn = document.getElementById('modal-ok-btn');

    // State Variables - Default activeTab to 'files'
    let activeTab = 'files';
    let selectedZipFiles = [];
    let selectedPdfFiles = [];
    let parsedData = [];
    let filteredData = [];
    let currentPage = 1;
    let pageSize = 50;

    // 1. Tab Switcher
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            uploadPanels.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            activeTab = btn.dataset.tab;
            document.getElementById(`panel-${activeTab}`).classList.add('active');
            checkReadyState();
        });
    });

    // 2. Drag and Drop Setup
    function setupDropzone(dropzone, input, onSelect) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('dragover');
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            onSelect(files);
        });

        input.addEventListener('change', () => {
            onSelect(input.files);
        });
    }

    setupDropzone(dropzoneZip, inputZip, (files) => {
        if (files && files.length > 0) {
            const zips = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.zip'));
            if (zips.length > 0) {
                selectedZipFiles = zips;
                const totalMB = (zips.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024)).toFixed(2);
                if (zips.length === 1) {
                    selectedZipBadge.textContent = `已选择 ZIP 压缩包: ${zips[0].name} (${totalMB} MB)`;
                } else {
                    const zipNames = zips.map(f => f.name).join(', ');
                    selectedZipBadge.textContent = `已选择 ${zips.length} 个 ZIP 压缩包: ${zipNames} (共 ${totalMB} MB)`;
                }
                selectedZipBadge.classList.remove('hidden');
                resetBtn.classList.remove('hidden');
            } else {
                alert('请选择以 .zip 结尾的压缩包文件。');
            }
        }
        checkReadyState();
    });

    setupDropzone(dropzoneFiles, inputFiles, (files) => {
        if (files && files.length > 0) {
            selectedPdfFiles = Array.from(files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
            selectedFilesBadge.textContent = `已选择 ${selectedPdfFiles.length} 份 PDF 报告文件`;
            selectedFilesBadge.classList.remove('hidden');
            resetBtn.classList.remove('hidden');
        }
        checkReadyState();
    });

    resetBtn.addEventListener('click', () => {
        selectedZipFiles = [];
        selectedPdfFiles = [];
        inputZip.value = '';
        inputFiles.value = '';
        selectedZipBadge.classList.add('hidden');
        selectedFilesBadge.classList.add('hidden');
        resetBtn.classList.add('hidden');
        checkReadyState();
    });

    function checkReadyState() {
        if (activeTab === 'zip') {
            startParseBtn.disabled = selectedZipFiles.length === 0;
        } else {
            startParseBtn.disabled = selectedPdfFiles.length === 0;
        }
    }

    // 3. Upload & Parse Execution (使用 XMLHttpRequest 实现 100% 物理真实字节进度条)
    startParseBtn.addEventListener('click', () => {
        const formData = new FormData();

        if (activeTab === 'zip' && selectedZipFiles.length > 0) {
            selectedZipFiles.forEach(f => formData.append('zip_files', f));
        } else if (activeTab === 'files' && selectedPdfFiles.length > 0) {
            selectedPdfFiles.forEach(f => formData.append('files', f));
        } else {
            return;
        }

        // 重置并显示真实进度条
        progressContainer.classList.remove('hidden');
        progressIconContainer.innerHTML = `<div class="spin-loader"></div>`;
        progressFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressStatusText.textContent = `正在准备发送文件...`;

        startParseBtn.disabled = true;

        const xhr = new XMLHttpRequest();
        let parseTimer = null;

        // 1. 真实网络上传物理字节监听 (映射进度 0% -> 70%)
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable && e.total > 0) {
                const uploadRatio = e.loaded / e.total;
                const pct = Math.min(70, Math.round(uploadRatio * 70));
                
                const loadedMB = (e.loaded / (1024 * 1024)).toFixed(1);
                const totalMB = (e.total / (1024 * 1024)).toFixed(1);

                progressFill.style.width = `${pct}%`;
                progressPercent.textContent = `${pct}%`;
                
                if (pct < 70) {
                    progressStatusText.textContent = `正在上传报告数据... (${loadedMB} MB / ${totalMB} MB)`;
                } else {
                    progressStatusText.textContent = `上传完成，后端正在准备接收解析...`;
                }
            }
        };

        // 2. 上传结束，进入后端并发解压与解析阶段 (映射进度 70% -> 95%)
        xhr.upload.onload = () => {
            let currentPct = 70;
            progressFill.style.width = '70%';
            progressPercent.textContent = '70%';
            progressStatusText.textContent = `正在解压与并发解析报告，请稍候...`;

            parseTimer = setInterval(() => {
                if (currentPct < 93) {
                    currentPct += 2;
                    progressFill.style.width = `${currentPct}%`;
                    progressPercent.textContent = `${currentPct}%`;
                }
            }, 300);
        };

        // 3. 服务端响应处理
        xhr.onload = () => {
            if (parseTimer) clearInterval(parseTimer);

            let res = null;
            try {
                res = JSON.parse(xhr.responseText);
            } catch (err) {
                progressContainer.classList.add('hidden');
                startParseBtn.disabled = false;
                alert(`服务器响应异常 (HTTP ${xhr.status})，未返回标准 JSON 数据。`);
                return;
            }

            if (xhr.status >= 200 && xhr.status < 300 && res && res.success) {
                progressFill.style.width = '100%';
                progressPercent.textContent = '100%';
                progressStatusText.textContent = `解析完成！成功提取 ${res.total} 份报告。`;
                
                // 更换为绿色成功 Checkmark 图标
                progressIconContainer.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                `;

                parsedData = res.data;
                updateStats(res.stats);
                applyFilterAndRender();

                downloadBtn.disabled = false;
                if (downloadWeeklyBtn) if (downloadWeeklyBtn) downloadWeeklyBtn.disabled = false;
                statsSection.classList.remove('hidden');
                resultsCard.classList.remove('hidden');

                setTimeout(() => {
                    resultsCard.scrollIntoView({ behavior: 'smooth' });
                }, 200);

            } else {
                progressContainer.classList.add('hidden');
                startParseBtn.disabled = false;
                alert(`解析出错: ${(res && res.error) ? res.error : '服务器内部错误'}`);
            }
        };

        // 4. 网络错误处理
        xhr.onerror = () => {
            if (parseTimer) clearInterval(parseTimer);
            progressContainer.classList.add('hidden');
            startParseBtn.disabled = false;
            alert('网络传输失败，请检查网络连接或服务器状态。');
        };

        xhr.open('POST', '/api/upload', true);
        xhr.send(formData);
    });

    const warningNoticeBanner = document.getElementById('warning-notice-banner');
    const warningNoticeText = document.getElementById('warning-notice-text');
    const btnFilterWarning = document.getElementById('btn-filter-warning');

    if (btnFilterWarning) {
        btnFilterWarning.addEventListener('click', () => {
            filterSelect.value = 'warning';
            applyFilterAndRender();
            resultsCard.scrollIntoView({ behavior: 'smooth' });
        });
    }

    // 4. Update Analytics Stats Cards
    function updateStats(stats) {
        document.getElementById('stat-total').textContent = stats.total || 0;
        document.getElementById('stat-sinus').textContent = stats.sinus_1 || 0;
        document.getElementById('stat-afib').textContent = stats.afib_2 || 0;
        document.getElementById('stat-svt').textContent = stats.svt_3 || 0;
        document.getElementById('stat-multi').textContent = stats.multi || 0;
        
        const statWarning = document.getElementById('stat-warning');
        if (statWarning) {
            statWarning.textContent = stats.warning_count || 0;
        }

        if (stats.warning_count > 0) {
            warningNoticeText.textContent = `本次解析检测到 ${stats.warning_count} 份报告需要人工核对负荷或持续时间，已为您自动高亮标注！`;
            warningNoticeBanner.classList.remove('hidden');
        } else {
            warningNoticeBanner.classList.add('hidden');
        }
    }

    // 5. Filter & Pagination Logic
    function applyFilterAndRender() {
        const query = searchInput.value.trim().toLowerCase();
        const filterVal = filterSelect.value;

        filteredData = parsedData.filter(item => {
            const subjid = String(item.SUBJID || '').toLowerCase();
            const filename = String(item._filename || '').toLowerCase();
            const result = String(item.ECGORRES || '');
            const cleanCode = result.replace(/\[|\]/g, '').trim();

            const matchQuery = subjid.includes(query) || filename.includes(query);

            let matchFilter = true;
            if (filterVal === '1') {
                matchFilter = (cleanCode === '1');
            } else if (filterVal === '2') {
                matchFilter = cleanCode.split(',').includes('2');
            } else if (filterVal === '3') {
                matchFilter = cleanCode.split(',').includes('3');
            } else if (filterVal === '2,3') {
                matchFilter = (cleanCode.includes(','));
            } else if (filterVal === 'warning') {
                matchFilter = Boolean(item.has_warning || (item.ECGATBURD && String(item.ECGATBURD).includes('人工检查')) || (item.warnings && item.warnings.length > 0));
            }

            return matchQuery && matchFilter;
        });

        currentPage = 1;
        renderTable();
    }

    searchInput.addEventListener('input', applyFilterAndRender);
    filterSelect.addEventListener('change', applyFilterAndRender);
    pageSizeSelect.addEventListener('change', () => {
        pageSize = parseInt(pageSizeSelect.value, 10);
        currentPage = 1;
        renderTable();
    });

    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });

    nextPageBtn.addEventListener('click', () => {
        const maxPage = Math.ceil(filteredData.length / pageSize) || 1;
        if (currentPage < maxPage) {
            currentPage++;
            renderTable();
        }
    });

    // 6. Render Data Table
    function renderTable() {
        const total = filteredData.length;
        const maxPage = Math.ceil(total / pageSize) || 1;

        if (currentPage > maxPage) currentPage = maxPage;

        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = Math.min(startIdx + pageSize, total);
        const pageItems = filteredData.slice(startIdx, endIdx);

        tableBody.innerHTML = '';

        if (pageItems.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="10" style="padding: 30px; color: #94a3b8;">未找到符合条件的数据项</td></tr>`;
        } else {
            pageItems.forEach((item, idx) => {
                const tr = document.createElement('tr');
                
                const isWarning = Boolean(item.has_warning || (item.ECGATBURD && String(item.ECGATBURD).includes('人工检查')) || (item.warnings && item.warnings.length > 0));
                if (isWarning) {
                    tr.classList.add('row-warning');
                }

                const code = String(item.ECGORRES || '/').trim();
                const cleanCode = code.replace(/\[|\]/g, '').trim();
                let badgeClass = 'badge-none';
                let badgeText = '/';

                if (cleanCode.includes(',')) {
                    badgeClass = 'badge-2-3';
                    badgeText = `2,3 复合多选`;
                } else if (cleanCode === '1') {
                    badgeClass = 'badge-1';
                    badgeText = '1 窦性心律';
                } else if (cleanCode === '2') {
                    badgeClass = 'badge-2';
                    badgeText = '2 房颤';
                } else if (cleanCode === '3') {
                    badgeClass = 'badge-3';
                    badgeText = '3 规则房速';
                } else if (cleanCode === '/' || cleanCode === '' || cleanCode === '解析失败') {
                    badgeClass = 'badge-none';
                    badgeText = cleanCode === '解析失败' ? '解析失败' : '/';
                }

                const durH = (item.ECGDURH !== undefined && item.ECGDURH !== null && item.ECGDURH !== '') ? item.ECGDURH : '0';
                const durM = (item.ECGDURM !== undefined && item.ECGDURM !== null && item.ECGDURM !== '') ? item.ECGDURM : '0';
                
                const atBurd = (item.ECGATBURD !== undefined && item.ECGATBURD !== null && item.ECGATBURD !== '') ? item.ECGATBURD : (cleanCode.includes('3') ? '0' : '/');
                const atH = (item.ECGATDURH !== undefined && item.ECGATDURH !== null && item.ECGATDURH !== '') ? item.ECGATDURH : (cleanCode.includes('3') ? '0' : '/');
                const atM = (item.ECGATDUR !== undefined && item.ECGATDUR !== null && item.ECGATDUR !== '') ? item.ECGATDUR : (cleanCode.includes('3') ? '0' : '/');
                const atS = (item.ECGATDURS !== undefined && item.ECGATDURS !== null && item.ECGATDURS !== '') ? item.ECGATDURS : (cleanCode.includes('3') ? '0' : '/');

                let atBurdHtml = escapeHtml(String(atBurd));
                if (String(atBurd).includes('人工检查')) {
                    atBurdHtml = `<span class="tag-warn-cell">${escapeHtml(String(atBurd))}</span>`;
                }

                tr.innerHTML = `
                    <td>${startIdx + idx + 1}</td>
                    <td><strong>${escapeHtml(item.SUBJID || item._filename || '/')}</strong> ${isWarning ? '<span class="warn-pill-sm">⚠️ 需核对</span>' : ''}</td>
                    <td>${escapeHtml(item.ECGSTDAT || '/')}</td>
                    <td>${escapeHtml(String(durH))} 小时 ${escapeHtml(String(durM))} 分</td>
                    <td><code>${escapeHtml(code)}</code></td>
                    <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                    <td>${escapeHtml(String(item.ECGHR !== undefined && item.ECGHR !== null ? item.ECGHR : '/'))}</td>
                    <td><pre style="margin:0; font-family:inherit; font-size:12px;">${atBurdHtml}</pre></td>
                    <td><pre style="margin:0; font-family:inherit; font-size:12px;">时: ${escapeHtml(String(atH))} | 分: ${escapeHtml(String(atM))} | 秒: ${escapeHtml(String(atS))}</pre></td>
                    <td><button class="btn-link" data-index="${startIdx + idx}">查看详情</button></td>
                `;
                tableBody.appendChild(tr);
            });

            document.querySelectorAll('.btn-link').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const itemIdx = parseInt(e.target.dataset.index, 10);
                    showDetailModal(filteredData[itemIdx]);
                });
            });
        }

        // Update Pagination Info
        pageStart.textContent = total > 0 ? startIdx + 1 : 0;
        pageEnd.textContent = endIdx;
        pageTotal.textContent = total;
        currentPageNum.textContent = `${currentPage} / ${maxPage}`;

        prevPageBtn.disabled = (currentPage <= 1);
        nextPageBtn.disabled = (currentPage >= maxPage);
    }

    // 7. Show Detail Modal
    function showDetailModal(item) {
        if (!item) return;
        modalTitle.textContent = `患者 [ ${item.SUBJID || item._filename} ] 全提取参数详情`;

        let html = '';
        const warnings = item.warnings || [];
        if (item.has_warning || warnings.length > 0 || (item.ECGATBURD && String(item.ECGATBURD).includes('人工检查'))) {
            html += `
                <div style="background: #fffbe6; border: 1.5px solid #fcd34d; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; color: #92400e; font-size: 13px;">
                    <div style="font-weight: 700; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                        ⚠️ 人工核对警示提醒：
                    </div>
                    <ul style="margin-left: 20px; margin-top: 4px; line-height: 1.6;">
            `;
            if (warnings.length > 0) {
                warnings.forEach(w => {
                    html += `<li>${escapeHtml(w)}</li>`;
                });
            } else if (item.ECGATBURD && String(item.ECGATBURD).includes('人工检查')) {
                html += `<li>报告结论确诊有房速且持续时间 >= 30s，但报告未打印房速占比原值，需人工核对</li>`;
            }
            html += `</ul></div>`;
        }

        const displayKeys = [
            { label: '受试者编号 (SUBJID)', key: 'SUBJID' },
            { label: '开始监测日期 (ECGSTDAT)', key: 'ECGSTDAT' },
            { label: '监测时长 (小时)', key: 'ECGDURH' },
            { label: '监测时长 (分)', key: 'ECGDURM' },
            { label: '分析时长 (小时)', key: 'ECGANADURH' },
            { label: '分析时长 (分)', key: 'ECGANADURM' },
            { label: '检查结果 (ECGORRES)', key: 'ECGORRES' },
            { label: '平均心率 (bpm)', key: 'ECGHR' },
            { label: '最大心率 (bpm)', key: 'ECGHRMAX' },
            { label: '最小心率 (bpm)', key: 'ECGHRMIN' },
            { label: '最长RR间期 (ms)', key: 'ECGRR' },
            { label: '房颤负荷 (%)', key: 'ECGAFBURD' },
            { label: '房颤持续时长 (小时)', key: 'ECGAFDURH' },
            { label: '房颤持续时长 (分)', key: 'ECGAFDUR' },
            { label: '规则房速负荷 (Col 27)', key: 'ECGATBURD' },
            { label: '规则房速最长持续时间 (小时)', key: 'ECGATDURH' },
            { label: '规则房速最长持续时间 (分)', key: 'ECGATDUR' },
            { label: '规则房速最长持续时间 (秒)', key: 'ECGATDURS' }
        ];

        html += `<div class="grid-fields">`;
        displayKeys.forEach(dk => {
            const val = item[dk.key] !== undefined ? item[dk.key] : '/';
            html += `
                <div class="field-box">
                    <div class="lbl">${dk.label}</div>
                    <div class="val-text">${escapeHtml(String(val))}</div>
                </div>
            `;
        });
        html += `</div>`;

        modalBody.innerHTML = html;
        detailModal.classList.remove('hidden');
    }

    [closeModalBtn, modalOkBtn].forEach(btn => {
        btn.addEventListener('click', () => {
            detailModal.classList.add('hidden');
        });
    });

    detailModal.addEventListener('click', (e) => {
        if (e.target === detailModal) {
            detailModal.classList.add('hidden');
        }
    });

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    const downloadWeeklyBtn = document.getElementById('download-weekly-btn');
    const inputStartdates = document.getElementById('input-startdates');
    const dropzoneStartdates = document.getElementById('dropzone-startdates');
    const startDatesStatusBadge = document.getElementById('start-dates-status-badge');

    const manageStartDatesBtn = document.getElementById('manage-start-dates-btn');
    const startDatesModal = document.getElementById('start-dates-modal');
    const closeStartDatesModalBtn = document.getElementById('close-start-dates-modal-btn');
    const saveStartDatesBtn = document.getElementById('save-start-dates-btn');
    const searchStartDatesInput = document.getElementById('search-start-dates-input');
    const addStartDateRowBtn = document.getElementById('add-start-date-row-btn');
    const startDatesTableBody = document.getElementById('start-dates-table-body');

    let currentStartDatesMap = {};

    // 8. 起始日期表上传 Dropzone
    if (dropzoneStartdates && inputStartdates) {
        setupDropzone(dropzoneStartdates, inputStartdates, (files) => {
            if (files && files.length > 0) {
                const file = files[0];
                if (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.csv')) {
                    uploadStartDatesFile(file);
                } else {
                    alert('请选择以 .xlsx 或 .csv 结尾的起始日期表文件。');
                }
            }
        });
    }

    function uploadStartDatesFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        startDatesStatusBadge.textContent = `正在上传并解析 ${file.name}...`;
        startDatesStatusBadge.className = 'file-name-badge';

        fetch('/api/upload_start_dates', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                currentStartDatesMap = res.start_dates || {};
                startDatesStatusBadge.textContent = `已成功载入 ${res.count} 位受试者起始日期 (去横杠匹配)`;
                startDatesStatusBadge.className = 'file-name-badge success';
                checkReadyState();
            } else {
                startDatesStatusBadge.textContent = `解析出错: ${res.error}`;
                startDatesStatusBadge.className = 'file-name-badge warning';
            }
        })
        .catch(err => {
            startDatesStatusBadge.textContent = `网络失败: ${err}`;
            startDatesStatusBadge.className = 'file-name-badge warning';
        });
    }

    // 9. 起始日期 Modal 管理弹窗
    if (manageStartDatesBtn) {
        manageStartDatesBtn.addEventListener('click', () => {
            fetch('/api/get_start_dates')
                .then(res => res.json())
                .then(res => {
                    if (res.success) {
                        currentStartDatesMap = res.start_dates || {};
                        renderStartDatesTable();
                        startDatesModal.classList.remove('hidden');
                    }
                });
        });
    }

    if (closeStartDatesModalBtn) {
        closeStartDatesModalBtn.addEventListener('click', () => {
            startDatesModal.classList.add('hidden');
        });
    }

    function renderStartDatesTable() {
        const query = (searchStartDatesInput ? searchStartDatesInput.value : '').trim().toLowerCase();
        startDatesTableBody.innerHTML = '';

        const keys = Object.keys(currentStartDatesMap).filter(k => k.toLowerCase().includes(query)).sort();
        if (keys.length === 0) {
            startDatesTableBody.innerHTML = `<tr><td colspan="3" style="padding: 20px; color: #94a3b8; text-align: center;">暂无受试者起始日期数据，可在上方直接点击上传《起始日期表.xlsx》或手动添加</td></tr>`;
            return;
        }

        keys.forEach(k => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code>${escapeHtml(k)}</code></td>
                <td><input type="date" class="custom-input start-date-val" data-id="${escapeHtml(k)}" value="${escapeHtml(currentStartDatesMap[k] || '')}" style="padding: 4px 8px; font-size: 13px; width: 100%;"></td>
                <td><button class="btn-link delete-start-date-btn" data-id="${escapeHtml(k)}" style="color: #ef4444;">删除</button></td>
            `;
            startDatesTableBody.appendChild(tr);
        });

        document.querySelectorAll('.delete-start-date-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const deleteId = e.target.dataset.id;
                delete currentStartDatesMap[deleteId];
                renderStartDatesTable();
            });
        });
    }

    if (searchStartDatesInput) {
        searchStartDatesInput.addEventListener('input', renderStartDatesTable);
    }

    if (addStartDateRowBtn) {
        addStartDateRowBtn.addEventListener('click', () => {
            const newId = prompt('请输入新受试者编号 (去除横杠后，例如 01001)：');
            if (newId) {
                const cleanNewId = newId.replace(/-/g, '').trim();
                const todayStr = new Date().toISOString().split('T')[0];
                currentStartDatesMap[cleanNewId] = todayStr;
                renderStartDatesTable();
            }
        });
    }

    if (saveStartDatesBtn) {
        saveStartDatesBtn.addEventListener('click', () => {
            document.querySelectorAll('.start-date-val').forEach(input => {
                const id = input.dataset.id;
                const val = input.value;
                if (id && val) {
                    currentStartDatesMap[id] = val;
                }
            });

            fetch('/api/get_start_dates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_dates: currentStartDatesMap })
            })
            .then(res => res.json())
            .then(res => {
                if (res.success) {
                    startDatesStatusBadge.textContent = `已成功保存 ${res.count} 位受试者起始日期`;
                    startDatesStatusBadge.className = 'file-name-badge success';
                    startDatesModal.classList.add('hidden');
                    checkReadyState();
                }
            });
        });
    }

    function checkReadyState() {
        if (activeTab === 'zip') {
            startParseBtn.disabled = selectedZipFiles.length === 0;
        } else {
            startParseBtn.disabled = selectedPdfFiles.length === 0;
        }
        if (parsedData && parsedData.length > 0) {
            downloadBtn.disabled = false;
                if (downloadWeeklyBtn) if (downloadWeeklyBtn) downloadWeeklyBtn.disabled = false;
            if (downloadWeeklyBtn) downloadWeeklyBtn.disabled = false;
        }
    }

    // 10. Download Excel Actions
    downloadBtn.addEventListener('click', () => {
        window.location.href = '/api/download';
    });

    if (downloadWeeklyBtn) {
        if (downloadWeeklyBtn) downloadWeeklyBtn.addEventListener('click', () => {
            window.location.href = '/api/download_weekly_summary';
        });
    }
});
