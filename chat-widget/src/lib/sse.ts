export interface SseEvent {
  event: string;
  data: string;
}

/** Incremental SSE parser. HTTP chunks do not need to align with SSE lines/events. */
export class SseParser {
  private buffer = "";

  feed(chunk: string, flush = false): SseEvent[] {
    this.buffer += chunk;
    const events: SseEvent[] = [];
    const separator = /\r\n\r\n|\n\n|\r\r/;

    while (true) {
      const match = separator.exec(this.buffer);
      if (!match) break;
      const raw = this.buffer.slice(0, match.index);
      this.buffer = this.buffer.slice(match.index + match[0].length);
      const event = parseEvent(raw);
      if (event) events.push(event);
    }

    if (flush && this.buffer.trim()) {
      const event = parseEvent(this.buffer);
      this.buffer = "";
      if (event) events.push(event);
    }
    return events;
  }
}

function parseEvent(raw: string): SseEvent | null {
  let event = "message";
  const data: string[] = [];

  for (const line of raw.split(/\r\n|\n|\r/)) {
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value || "message";
    if (field === "data") data.push(value);
  }

  return data.length ? { event, data: data.join("\n") } : null;
}
