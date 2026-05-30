import { useEffect, useMemo, useRef } from 'react'
import {
  findDiffRowIndex,
  makeDiffRowKey,
  parsePatch,
} from '../../utils/formatters'
import {
  FILE_STATUS_LABELS,
  FILE_TYPE_LABELS,
  REVIEW_STRATEGY_LABELS,
} from '../../utils/constants'
import { labelFrom } from '../../utils/formatters'
import EmptyState from '../common/EmptyState'

export default function DiffViewer({ file, focusedFinding }) {
  const diffRowRefs = useRef(new Map())
  const rows = useMemo(() => (file ? parsePatch(file.patch) : []), [file])
  const focusedIndex = useMemo(() => {
    if (!file || !focusedFinding || focusedFinding.file_path !== file.filename) {
      return -1
    }
    return findDiffRowIndex(rows, focusedFinding.line)
  }, [file, focusedFinding, rows])

  useEffect(() => {
    if (!file || focusedIndex < 0) {
      return
    }
    const row = diffRowRefs.current.get(makeDiffRowKey(file.filename, focusedIndex))
    row?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [file, focusedIndex])

  if (!file) {
    return <EmptyState>No changed file selected.</EmptyState>
  }

  return (
    <div className="diff-viewer">
      <div className="diff-toolbar">
        <div>
          <strong translate="no">{file.filename}</strong>
          <small>
            {labelFrom(FILE_STATUS_LABELS, file.status)} ·{' '}
            {FILE_TYPE_LABELS[file.file_type] || file.file_type} ·{' '}
            {REVIEW_STRATEGY_LABELS[file.review_strategy] || file.review_strategy}
          </small>
        </div>
        <span>
          +{file.additions} -{file.deletions}
        </span>
      </div>

      {rows.length ? (
        <div className="diff-table" translate="no">
          {rows.map((row, index) => {
            const rowKey = makeDiffRowKey(file.filename, index)
            const isFocused = index === focusedIndex
            return (
              <div
                className={`diff-row ${row.kind}${isFocused ? ' focused' : ''}`}
                key={`${row.kind}-${index}-${row.oldLine}-${row.newLine}`}
                ref={(node) => {
                  if (node) {
                    diffRowRefs.current.set(rowKey, node)
                  } else {
                    diffRowRefs.current.delete(rowKey)
                  }
                }}
              >
                <span className="line-number">{row.oldLine}</span>
                <span className="line-number">{row.newLine}</span>
                <code>{row.content || ' '}</code>
              </div>
            )
          })}
        </div>
      ) : (
        <EmptyState>GitHub did not return a textual diff for this file.</EmptyState>
      )}

      {file.patch_truncated ? (
        <p className="patch-note">Diff preview was truncated before review.</p>
      ) : null}
    </div>
  )
}
