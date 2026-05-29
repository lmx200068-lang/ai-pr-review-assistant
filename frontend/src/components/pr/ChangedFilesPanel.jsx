import { useEffect, useMemo, useRef } from 'react'
import {
  FILE_STATUS_LABELS,
  FILE_TYPE_LABELS,
  REVIEW_STRATEGY_LABELS,
} from '../../utils/constants'
import { labelFrom } from '../../utils/formatters'
import DiffViewer from './DiffViewer'

export default function ChangedFilesPanel({
  files,
  selectedFileName,
  onSelectFile,
  focusedFinding,
}) {
  const sourceReviewRef = useRef(null)
  const selectedFile = useMemo(
    () =>
      files.find((file) => file.filename === selectedFileName) ||
      files[0] ||
      null,
    [files, selectedFileName],
  )

  useEffect(() => {
    if (!focusedFinding) {
      return
    }
    sourceReviewRef.current?.scrollIntoView({
      block: 'start',
      behavior: 'smooth',
    })
  }, [focusedFinding])

  if (!files.length) {
    return null
  }

  return (
    <section
      className="source-review"
      ref={sourceReviewRef}
      aria-label="变更源码"
    >
      <div className="changed-files-header">
        <h3>PR 变更文件</h3>
        <span>已加载 {files.length} 个文件</span>
      </div>

      <div className="source-layout">
        <div className="changed-file-list" aria-label="变更文件">
          {files.map((file) => (
            <button
              className={
                selectedFile?.filename === file.filename
                  ? 'changed-file selected'
                  : 'changed-file'
              }
              key={file.filename}
              onClick={() => onSelectFile(file.filename)}
              type="button"
            >
              <span>
                <strong translate="no">{file.filename}</strong>
                <small>
                  {labelFrom(FILE_STATUS_LABELS, file.status)} ·{' '}
                  {FILE_TYPE_LABELS[file.file_type] || file.file_type} ·{' '}
                  {REVIEW_STRATEGY_LABELS[file.review_strategy] ||
                    file.review_strategy}
                </small>
              </span>
              <span className="file-stats">
                <span>+{file.additions}</span>
                <span>-{file.deletions}</span>
                <span>{file.changes} 处变更</span>
              </span>
            </button>
          ))}
        </div>

        <DiffViewer file={selectedFile} focusedFinding={focusedFinding} />
      </div>
    </section>
  )
}
