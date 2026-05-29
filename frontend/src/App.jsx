import { useEffect, useState } from 'react'
import './App.css'
import ErrorBanner from './components/common/ErrorBanner'
import AppShell from './components/layout/AppShell'
import Header from './components/layout/Header'
import ChangedFilesPanel from './components/pr/ChangedFilesPanel'
import PrOverview from './components/pr/PrOverview'
import ContextSummary from './components/review/ContextSummary'
import FindingsList from './components/review/FindingsList'
import PendingFindings from './components/review/PendingFindings'
import ReviewForm from './components/review/ReviewForm'
import ReviewSummary from './components/review/ReviewSummary'
import TaskProgress from './components/review/TaskProgress'
import TaskHistory from './components/tasks/TaskHistory'
import { useHealth } from './hooks/useHealth'
import { useReviewTaskPolling } from './hooks/useReviewTaskPolling'
import { useReviewTasks } from './hooks/useReviewTasks'
import { isReviewingTask } from './utils/formatters'

export default function App() {
  const { health, loading: healthLoading, error: healthError } = useHealth()
  const {
    tasks,
    activeTask,
    createTask,
    selectTask,
    loading: tasksLoading,
    creating,
    error: tasksError,
  } = useReviewTasks()
  const [selectedFileName, setSelectedFileName] = useState('')
  const [focusedFinding, setFocusedFinding] = useState(null)

  const polling = useReviewTaskPolling(
    activeTask?.id,
    Boolean(activeTask?.id && isReviewingTask(activeTask)),
  )

  useEffect(() => {
    if (polling.task) {
      selectTask(polling.task)
    }
  }, [polling.task, selectTask])

  useEffect(() => {
    setFocusedFinding(null)
    setSelectedFileName('')
  }, [activeTask?.id])

  async function handleCreateTask(payload) {
    setFocusedFinding(null)
    setSelectedFileName('')
    await createTask(payload)
  }

  function handleSelectFinding(finding) {
    setFocusedFinding({
      id: finding.id,
      file_path: finding.file_path,
      line: finding.line,
    })
    setSelectedFileName(finding.file_path)
  }

  const combinedError = tasksError || polling.error || healthError
  const findings = activeTask?.findings || []
  const pendingFindings = activeTask?.pending_findings || []

  return (
    <AppShell
      header={<Header health={health} loading={healthLoading} />}
      error={<ErrorBanner message={combinedError} />}
    >
      <ReviewForm
        githubAccess={health?.github_access || 'read_only'}
        loading={creating}
        onSubmit={handleCreateTask}
      />

      <TaskProgress task={activeTask} />

      <TaskHistory
        activeTaskId={activeTask?.id}
        loading={tasksLoading}
        onSelect={selectTask}
        tasks={tasks}
      />

      <section className="tool-panel findings-panel">
        <div className="panel-heading">
          <p className="eyebrow">评审输出</p>
          <h2>
            {findings.length || pendingFindings.length
              ? `${findings.length} 条正式发现，${pendingFindings.length} 条待确认建议`
              : '评审结果'}
          </h2>
        </div>

        <PrOverview pr={activeTask?.pr} />
        <ContextSummary contextSummary={activeTask?.context_summary} />
        <ReviewSummary task={activeTask} />

        <ChangedFilesPanel
          files={activeTask?.changed_files || []}
          focusedFinding={focusedFinding}
          onSelectFile={setSelectedFileName}
          selectedFileName={selectedFileName}
        />

        <FindingsList
          findings={findings}
          focusedFinding={focusedFinding}
          onSelectFinding={handleSelectFinding}
          task={activeTask}
        />

        <PendingFindings
          focusedFinding={focusedFinding}
          onSelectFinding={handleSelectFinding}
          pendingFindings={pendingFindings}
        />
      </section>
    </AppShell>
  )
}
