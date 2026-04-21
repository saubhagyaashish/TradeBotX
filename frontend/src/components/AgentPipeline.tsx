// AgentPipeline — live progress stepper for the 13-agent pipeline

import { PIPELINE } from '../types'

interface AgentPipelineProps {
  completedAgents: Set<string>
  isRunning: boolean
}

export default function AgentPipeline({ completedAgents, isRunning }: AgentPipelineProps) {
  const currentStep = PIPELINE.find((p) => !completedAgents.has(p))

  return (
    <div className="pipeline-card">
      <div className="pipeline-header">
        <span className="pipeline-label">Agent Pipeline</span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginLeft: '0.5rem' }}>
          {completedAgents.size} / {PIPELINE.length} completed
        </span>
        {isRunning && <span className="pipeline-live-dot" />}
      </div>

      <div className="pipeline-grid">
        {PIPELINE.map((name) => {
          const done = completedAgents.has(name)
          const active = !done && name === currentStep && isRunning
          return (
            <div
              key={name}
              className={`pipeline-step ${done ? 'done' : ''} ${active ? 'active' : ''}`}
            >
              <span className="pipeline-dot" />
              {name}
            </div>
          )
        })}
      </div>
    </div>
  )
}
