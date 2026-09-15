import type { EyeChat, ChatTimeWindow } from './useEyeChat';
import { EyeSourceFilter } from './EyeSourceFilter';
import { useAssistantMapAvailability } from '@/lib/assistantMapContext';

export function EyeMapControls({
  chat,
  scopeId,
  timeId,
}: {
  chat: EyeChat;
  scopeId: string;
  timeId: string;
}) {
  const map = useAssistantMapAvailability();
  return (
    <>
      <div className="eye-search-controls">
        <div className="eye-scope">
          <label htmlFor={scopeId}>Area</label>
          <select
            id={scopeId}
            aria-label="Eye search scope"
            value={chat.scope}
            disabled={chat.busy}
            onChange={(event) => {
              const value = event.target.value;
              if (value === 'global' || value === 'viewport' || value === 'selected')
                chat.setScope(value);
            }}
          >
            <option value="global">All sources</option>
            <option value="viewport" disabled={!map?.bounds}>
              Map view
            </option>
            <option value="selected" disabled={!map?.selected}>
              Selected item
            </option>
          </select>
        </div>
        <div className="eye-scope">
          <label htmlFor={timeId}>Time</label>
          <select
            id={timeId}
            aria-label="Eye time period"
            value={chat.timeWindow}
            disabled={chat.busy}
            onChange={(event) => chat.setTimeWindow(event.target.value as ChatTimeWindow)}
          >
            <option value="auto">From question</option>
            <option value="48">Past 2 days</option>
            <option value="120">Past 5 days</option>
            <option value="168">Past 7 days</option>
            <option value="336">Past 14 days</option>
            <option value="720">Past 30 days</option>
            <option value="2160">Past 90 days</option>
            <option value="8760">Past year</option>
          </select>
        </div>
      </div>
      {chat.timeWindow !== 'auto' && (
        <p className="eye-scope-note">Filters by publication time. Source archives vary.</p>
      )}
      {chat.scope === 'viewport' && (
        <p className="eye-scope-note">
          Uses the current geographic view boundary, including layers switched off.
        </p>
      )}
      {chat.scope === 'selected' && (
        <p className="eye-scope-note">
          {map?.selected ? map.selected.title : 'Select an item on the map to continue.'}
        </p>
      )}
      <EyeSourceFilter
        value={chat.sourceCategories}
        onChange={chat.setSourceCategories}
        disabled={chat.busy}
      />
    </>
  );
}
