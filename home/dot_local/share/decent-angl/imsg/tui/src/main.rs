use std::io::{self, Stdout};
use std::process::Command;
use std::time::{Duration, Instant};

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{
    Block, Borders, List, ListItem, ListState, Paragraph, Wrap,
};
use ratatui::{Frame, Terminal};
use serde::de::Error as _;
use serde::de::DeserializeOwned;
use serde::Deserialize;

type AppResult<T> = Result<T, String>;

fn deserialize_boolish<'de, D>(deserializer: D) -> Result<bool, D::Error>
where
    D: serde::Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum Boolish {
        Bool(bool),
        Int(i64),
        Text(String),
    }

    let value = Option::<Boolish>::deserialize(deserializer)?;
    match value {
        None => Ok(false),
        Some(Boolish::Bool(value)) => Ok(value),
        Some(Boolish::Int(value)) => Ok(value != 0),
        Some(Boolish::Text(value)) => {
            let normalized = value.trim().to_ascii_lowercase();
            match normalized.as_str() {
                "" | "0" | "false" | "no" | "off" => Ok(false),
                "1" | "true" | "yes" | "on" => Ok(true),
                _ => Err(D::Error::custom(format!("unsupported boolish value: {value}"))),
            }
        }
    }
}

fn deserialize_stringish<'de, D>(deserializer: D) -> Result<String, D::Error>
where
    D: serde::Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum Stringish {
        Text(String),
        Int(i64),
        Float(f64),
        Bool(bool),
    }

    let value = Option::<Stringish>::deserialize(deserializer)?;
    let rendered = match value {
        None => String::new(),
        Some(Stringish::Text(value)) => value,
        Some(Stringish::Int(value)) => value.to_string(),
        Some(Stringish::Float(value)) => value.to_string(),
        Some(Stringish::Bool(value)) => value.to_string(),
    };
    Ok(rendered)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Pane {
    Chats,
    Messages,
    Lower,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum InputMode {
    Normal,
    Search,
    Compose,
    Reply,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum LowerView {
    Search,
    Outbox,
    Help,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct ChatSummary {
    chat_rowid: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    title: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    participants: String,
    #[serde(default)]
    message_count: i64,
    #[serde(default)]
    unread_count: i64,
    #[serde(default)]
    last_message_at: Option<String>,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    last_message_preview: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct AttachmentRow {
    #[serde(default)]
    attachment_rowid: i64,
    #[serde(default)]
    timestamp: Option<String>,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    sender: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    transfer_name: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    filename: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    mime_type: String,
    #[serde(default)]
    total_bytes: i64,
    #[serde(default, deserialize_with = "deserialize_boolish")]
    path_exists: bool,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct MessageRow {
    #[serde(default)]
    message_rowid: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    guid: String,
    #[serde(default)]
    handle_id: Option<String>,
    #[serde(default)]
    handle_display: Option<String>,
    #[serde(default)]
    is_from_me: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    preview: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    kind: String,
    #[serde(default)]
    timestamp: Option<String>,
    #[serde(default)]
    reply_target_preview: Option<String>,
    #[serde(default)]
    attachments: Vec<AttachmentRow>,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct ShowResponse {
    chat: ChatSummary,
    #[serde(default)]
    messages: Vec<MessageRow>,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct SearchResultRow {
    #[serde(default)]
    chat_rowid: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    chat_title: String,
    #[serde(default)]
    message_rowid: i64,
    #[serde(default)]
    handle_id: Option<String>,
    #[serde(default)]
    handle_display: Option<String>,
    #[serde(default)]
    is_from_me: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    preview: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    kind: String,
    #[serde(default)]
    timestamp: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct SendJobRow {
    #[serde(default)]
    job_rowid: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    status: String,
    #[serde(default)]
    created_at: Option<String>,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    requested_by_machine_id: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    resolved_recipient: String,
    #[serde(default)]
    recipient_input: Option<String>,
    #[serde(default)]
    attempt_count: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    blocked_reason: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    provider_detail: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    message_text: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Deserialize, Default)]
struct SendResponse {
    #[serde(default, deserialize_with = "deserialize_boolish")]
    ok: bool,
    #[serde(default)]
    status: String,
    #[serde(default)]
    detail: String,
    #[serde(default)]
    blocked_reason: String,
    #[serde(default)]
    recipient: String,
    #[serde(default)]
    destination_chat_rowid: Option<i64>,
}

#[derive(Debug)]
struct App {
    chats: Vec<ChatSummary>,
    chats_state: ListState,
    messages: Vec<MessageRow>,
    messages_state: ListState,
    attachments: Vec<AttachmentRow>,
    search_results: Vec<SearchResultRow>,
    lower_state: ListState,
    outbox: Vec<SendJobRow>,
    pane: Pane,
    input_mode: InputMode,
    lower_view: Option<LowerView>,
    input: String,
    status: String,
    unreads_only: bool,
    quit: bool,
    loaded_chat_rowid: Option<i64>,
    pending_chat_rowid: Option<i64>,
    last_chat_selection_change: Instant,
    last_tick: Instant,
    tick_rate: Duration,
    chat_selection_delay: Duration,
}

impl App {
    fn new() -> Self {
        Self {
            chats: Vec::new(),
            chats_state: ListState::default(),
            messages: Vec::new(),
            messages_state: ListState::default(),
            attachments: Vec::new(),
            search_results: Vec::new(),
            lower_state: ListState::default(),
            outbox: Vec::new(),
            pane: Pane::Chats,
            input_mode: InputMode::Normal,
            lower_view: None,
            input: String::new(),
            status: "Loading imsg…".to_string(),
            unreads_only: false,
            quit: false,
            loaded_chat_rowid: None,
            pending_chat_rowid: None,
            last_chat_selection_change: Instant::now(),
            last_tick: Instant::now(),
            tick_rate: Duration::from_secs(30),
            chat_selection_delay: Duration::from_millis(160),
        }
    }

    fn selected_chat(&self) -> Option<&ChatSummary> {
        self.chats_state.selected().and_then(|idx| self.chats.get(idx))
    }

    fn selected_message(&self) -> Option<&MessageRow> {
        self.messages_state
            .selected()
            .and_then(|idx| self.messages.get(idx))
    }

    fn selected_chat_rowid(&self) -> Option<i64> {
        self.selected_chat().map(|chat| chat.chat_rowid)
    }

    fn selected_message_rowid(&self) -> Option<i64> {
        self.selected_message().map(|message| message.message_rowid)
    }

    fn selected_search_result(&self) -> Option<&SearchResultRow> {
        self.lower_state
            .selected()
            .and_then(|idx| self.search_results.get(idx))
    }

    fn selected_outbox(&self) -> Option<&SendJobRow> {
        self.lower_state.selected().and_then(|idx| self.outbox.get(idx))
    }

    fn refresh_all(&mut self) -> AppResult<()> {
        self.refresh_chats()?;
        self.refresh_current_chat()?;
        self.refresh_outbox()?;
        self.last_tick = Instant::now();
        Ok(())
    }

    fn refresh_chats(&mut self) -> AppResult<()> {
        let selected_chat_rowid = self.selected_chat_rowid();
        let args = if self.unreads_only {
            vec!["unreads".to_string(), "--limit".to_string(), "80".to_string(), "--json".to_string()]
        } else {
            vec!["chats".to_string(), "--limit".to_string(), "80".to_string(), "--json".to_string()]
        };
        self.chats = run_imsg_json::<Vec<ChatSummary>>(&args)?;
        if self.chats.is_empty() {
            self.chats_state.select(None);
        } else {
            let idx = selected_chat_rowid
                .and_then(|chat_rowid| self.chats.iter().position(|chat| chat.chat_rowid == chat_rowid))
                .unwrap_or(0)
                .min(self.chats.len() - 1);
            self.chats_state.select(Some(idx));
        }
        Ok(())
    }

    fn refresh_current_chat(&mut self) -> AppResult<()> {
        let Some(chat_rowid) = self.selected_chat_rowid() else {
            self.messages.clear();
            self.messages_state.select(None);
            self.attachments.clear();
            self.loaded_chat_rowid = None;
            self.pending_chat_rowid = None;
            return Ok(());
        };
        let previous_message_rowid = if self.loaded_chat_rowid == Some(chat_rowid) {
            self.selected_message_rowid()
        } else {
            None
        };
        let args = vec![
            "show".to_string(),
            chat_rowid.to_string(),
            "--limit".to_string(),
            "60".to_string(),
            "--json".to_string(),
        ];
        let response = run_imsg_json::<ShowResponse>(&args)?;
        self.messages = response.messages;
        if self.messages.is_empty() {
            self.messages_state.select(None);
        } else {
            let idx = previous_message_rowid
                .and_then(|message_rowid| {
                    self.messages
                        .iter()
                        .position(|message| message.message_rowid == message_rowid)
                })
                .unwrap_or(self.messages.len().saturating_sub(1))
                .min(self.messages.len() - 1);
            self.messages_state.select(Some(idx));
        }
        self.loaded_chat_rowid = Some(chat_rowid);
        self.pending_chat_rowid = None;
        Ok(())
    }

    fn queue_current_chat_refresh(&mut self) {
        self.pending_chat_rowid = self.selected_chat_rowid();
        self.last_chat_selection_change = Instant::now();
    }

    fn maybe_refresh_pending_chat(&mut self) -> AppResult<()> {
        let Some(chat_rowid) = self.pending_chat_rowid else {
            return Ok(());
        };
        if self.last_chat_selection_change.elapsed() < self.chat_selection_delay {
            return Ok(());
        }
        if self.loaded_chat_rowid == Some(chat_rowid) {
            self.pending_chat_rowid = None;
            return Ok(());
        }
        self.refresh_current_chat()
    }

    fn refresh_outbox(&mut self) -> AppResult<()> {
        let args = vec![
            "outbox".to_string(),
            "--limit".to_string(),
            "40".to_string(),
            "--json".to_string(),
        ];
        self.outbox = run_imsg_json::<Vec<SendJobRow>>(&args)?;
        if self.outbox.is_empty() {
            self.lower_state.select(None);
        } else if self.lower_view == Some(LowerView::Outbox) {
            let idx = self.lower_state.selected().unwrap_or(0).min(self.outbox.len() - 1);
            self.lower_state.select(Some(idx));
        }
        Ok(())
    }

    fn refresh_attachments(&mut self) -> AppResult<()> {
        let Some(chat) = self.selected_chat() else {
            self.attachments.clear();
            return Ok(());
        };
        let args = vec![
            "attachments".to_string(),
            chat.chat_rowid.to_string(),
            "--limit".to_string(),
            "24".to_string(),
            "--json".to_string(),
        ];
        #[derive(Debug, Deserialize)]
        struct AttachmentResponse {
            #[serde(default)]
            attachments: Vec<AttachmentRow>,
        }
        let response = run_imsg_json::<AttachmentResponse>(&args)?;
        self.attachments = response.attachments;
        Ok(())
    }

    fn run_search(&mut self) -> AppResult<()> {
        let query = self.input.trim();
        if query.is_empty() {
            self.search_results.clear();
            self.lower_state.select(None);
            self.lower_view = None;
            self.status = "Search cleared".to_string();
            return Ok(());
        }
        let args = vec![
            "search".to_string(),
            query.to_string(),
            "--limit".to_string(),
            "40".to_string(),
            "--json".to_string(),
        ];
        self.search_results = run_imsg_json::<Vec<SearchResultRow>>(&args)?;
        self.lower_view = Some(LowerView::Search);
        if self.search_results.is_empty() {
            self.lower_state.select(None);
            self.status = format!("No results for {}", query);
        } else {
            self.lower_state.select(Some(0));
            self.pane = Pane::Lower;
            self.status = format!("{} search results", self.search_results.len());
        }
        Ok(())
    }

    fn send_input(&mut self, reply: bool) -> AppResult<()> {
        let text = self.input.trim().to_string();
        if text.is_empty() {
            self.status = "Message cannot be empty".to_string();
            return Ok(());
        }
        let args = if reply {
            let Some(message) = self.selected_message() else {
                self.status = "No message selected to reply to".to_string();
                return Ok(());
            };
            vec![
                "reply".to_string(),
                "--message".to_string(),
                message.message_rowid.to_string(),
                "--text".to_string(),
                text.clone(),
                "--json".to_string(),
            ]
        } else {
            let Some(chat) = self.selected_chat() else {
                self.status = "No chat selected".to_string();
                return Ok(());
            };
            vec![
                "send".to_string(),
                "--chat".to_string(),
                chat.chat_rowid.to_string(),
                "--text".to_string(),
                text.clone(),
                "--json".to_string(),
            ]
        };
        let response = run_imsg_json_allow_failure::<SendResponse>(&args)?;
        self.status = if response.ok {
            format!("Sent: {}", compact_string(&text, 80))
        } else if !response.blocked_reason.is_empty() {
            format!("Blocked: {}", response.blocked_reason)
        } else {
            compact_string(&response.detail, 120)
        };
        self.input.clear();
        self.input_mode = InputMode::Normal;
        self.refresh_all()?;
        Ok(())
    }

    fn retry_selected_outbox(&mut self) -> AppResult<()> {
        let Some(job) = self.selected_outbox() else {
            self.status = "No outbox job selected".to_string();
            return Ok(());
        };
        let mut args = vec![
            "retry".to_string(),
            job.job_rowid.to_string(),
            "--json".to_string(),
        ];
        if job.status == "blocked" && job.blocked_reason == "duplicate-send-protection" {
            args.insert(2, "--allow-duplicate".to_string());
        }
        let response = run_imsg_json_allow_failure::<SendResponse>(&args)?;
        self.status = if response.ok {
            format!("Retry sent: {}", compact_string(&job.message_text, 80))
        } else if !response.blocked_reason.is_empty() {
            format!("Retry blocked: {}", response.blocked_reason)
        } else {
            compact_string(&response.detail, 120)
        };
        self.refresh_all()?;
        Ok(())
    }

    fn activate_selected_search_result(&mut self) -> AppResult<()> {
        let Some(result) = self.selected_search_result().cloned() else {
            return Ok(());
        };
        if let Some(position) = self
            .chats
            .iter()
            .position(|chat| chat.chat_rowid == result.chat_rowid)
        {
            self.chats_state.select(Some(position));
        } else {
            self.status = "Search hit points to a chat outside the current list".to_string();
            return Ok(());
        }
        self.pane = Pane::Messages;
        self.refresh_current_chat()?;
        if let Some(position) = self
            .messages
            .iter()
            .position(|message| message.message_rowid == result.message_rowid)
        {
            self.messages_state.select(Some(position));
        }
        self.status = format!("Opened {}", result.chat_title);
        Ok(())
    }

    fn cycle_focus(&mut self) {
        self.pane = match (self.pane, self.lower_view) {
            (Pane::Chats, _) => Pane::Messages,
            (Pane::Messages, Some(_)) => Pane::Lower,
            (Pane::Messages, None) => Pane::Chats,
            (Pane::Lower, _) => Pane::Chats,
        };
    }

    fn move_selection_down(&mut self) {
        match self.pane {
            Pane::Chats => move_list_state(&mut self.chats_state, self.chats.len(), 1),
            Pane::Messages => move_list_state(&mut self.messages_state, self.messages.len(), 1),
            Pane::Lower => {
                let len = match self.lower_view {
                    Some(LowerView::Search) => self.search_results.len(),
                    Some(LowerView::Outbox) => self.outbox.len(),
                    Some(LowerView::Help) | None => 0,
                };
                move_list_state(&mut self.lower_state, len, 1);
            }
        }
    }

    fn move_selection_up(&mut self) {
        match self.pane {
            Pane::Chats => move_list_state(&mut self.chats_state, self.chats.len(), -1),
            Pane::Messages => move_list_state(&mut self.messages_state, self.messages.len(), -1),
            Pane::Lower => {
                let len = match self.lower_view {
                    Some(LowerView::Search) => self.search_results.len(),
                    Some(LowerView::Outbox) => self.outbox.len(),
                    Some(LowerView::Help) | None => 0,
                };
                move_list_state(&mut self.lower_state, len, -1);
            }
        }
    }

    fn on_tick(&mut self) -> AppResult<()> {
        if self.last_tick.elapsed() >= self.tick_rate && self.input_mode == InputMode::Normal {
            let current_chat_rowid = self.selected_chat_rowid();
            self.refresh_chats()?;
            if self.selected_chat_rowid().is_some() {
                if self.selected_chat_rowid() != current_chat_rowid
                    || self.loaded_chat_rowid != self.selected_chat_rowid()
                {
                    self.refresh_current_chat()?;
                } else {
                    self.refresh_current_chat()?;
                }
            }
            if self.lower_view == Some(LowerView::Outbox) {
                self.refresh_outbox()?;
            }
            self.last_tick = Instant::now();
        }
        Ok(())
    }
}

fn move_list_state(state: &mut ListState, len: usize, delta: isize) {
    if len == 0 {
        state.select(None);
        return;
    }
    let current = state.selected().unwrap_or(0) as isize;
    let next = (current + delta).clamp(0, (len as isize) - 1) as usize;
    state.select(Some(next));
}

fn compact_string(value: &str, limit: usize) -> String {
    let collapsed = value.split_whitespace().collect::<Vec<_>>().join(" ");
    if collapsed.len() <= limit {
        return collapsed;
    }
    format!("{}...", &collapsed[..limit.saturating_sub(3)])
}

fn looks_like_opaque_chat_id(value: &str) -> bool {
    let trimmed = value.trim();
    let lower = trimmed.to_ascii_lowercase();
    if !lower.starts_with("chat") {
        return false;
    }
    let suffix = &lower[4..];
    !suffix.is_empty() && suffix.chars().all(|character| character.is_ascii_digit())
}

fn summarize_participants(value: &str, limit_entries: usize) -> String {
    let entries: Vec<String> = value
        .split(',')
        .map(|entry| entry.trim())
        .filter(|entry| !entry.is_empty())
        .map(|entry| entry.to_string())
        .collect();
    if entries.is_empty() {
        return String::new();
    }
    if entries.len() <= limit_entries {
        return entries.join(", ");
    }
    format!(
        "{} +{}",
        entries[..limit_entries].join(", "),
        entries.len().saturating_sub(limit_entries)
    )
}

fn friendly_timestamp(value: Option<&str>) -> String {
    let Some(raw_value) = value else {
        return "unknown".to_string();
    };
    let normalized = raw_value.trim().replace('T', " ");
    if normalized.len() >= 16 {
        normalized[..16].to_string()
    } else if normalized.is_empty() {
        "unknown".to_string()
    } else {
        normalized
    }
}

fn message_actor_label(is_from_me: i64, handle_display: Option<&str>, handle_id: Option<&str>) -> String {
    if is_from_me != 0 {
        return "You".to_string();
    }
    handle_display
        .filter(|value| !value.trim().is_empty())
        .or(handle_id)
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "Unknown".to_string())
}

fn chat_label(chat: &ChatSummary) -> String {
    let title = chat.title.trim();
    if !title.is_empty() && !looks_like_opaque_chat_id(title) {
        return title.to_string();
    }
    let participants = summarize_participants(&chat.participants, 3);
    if !participants.is_empty() {
        return participants;
    }
    if !title.is_empty() {
        return title.to_string();
    }
    format!("chat {}", chat.chat_rowid)
}

fn chat_subtitle(chat: &ChatSummary) -> String {
    let preview = compact_string(&chat.last_message_preview, 80);
    if !preview.is_empty() && preview != "[empty]" {
        return preview;
    }
    let participants = summarize_participants(&chat.participants, 4);
    if !participants.is_empty() && participants != chat_label(chat) {
        return participants;
    }
    "No recent preview".to_string()
}

fn run_imsg_json<T: DeserializeOwned>(args: &[String]) -> AppResult<T> {
    let output = Command::new("imsg")
        .args(args)
        .output()
        .map_err(|error| format!("failed to run imsg: {error}"))?;
    if !output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        let detail = if !stdout.trim().is_empty() { stdout } else { stderr };
        return Err(detail.trim().to_string());
    }
    serde_json::from_slice::<T>(&output.stdout)
        .map_err(|error| format!("failed to decode imsg json: {error}"))
}

fn run_imsg_json_allow_failure<T: DeserializeOwned>(args: &[String]) -> AppResult<T> {
    let output = Command::new("imsg")
        .args(args)
        .output()
        .map_err(|error| format!("failed to run imsg: {error}"))?;
    if !output.stdout.is_empty() {
        serde_json::from_slice::<T>(&output.stdout)
            .map_err(|error| format!("failed to decode imsg json: {error}"))
    } else if !output.status.success() {
        Err(String::from_utf8_lossy(&output.stderr).trim().to_string())
    } else {
        Err("imsg returned no json payload".to_string())
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;
    let result = run_app(&mut terminal);
    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    terminal.show_cursor()?;
    if let Err(error) = result {
        eprintln!("{error}");
        std::process::exit(1);
    }
    Ok(())
}

fn run_app(terminal: &mut Terminal<CrosstermBackend<Stdout>>) -> AppResult<()> {
    let mut app = App::new();
    if let Err(error) = app.refresh_all() {
        app.status = error;
    } else {
        app.status = "imsg ready".to_string();
    }

    loop {
        terminal
            .draw(|frame| draw(frame, &app))
            .map_err(|error| error.to_string())?;

        if app.quit {
            break;
        }

        if event::poll(Duration::from_millis(200)).map_err(|error| error.to_string())? {
            if let Event::Key(key) = event::read().map_err(|error| error.to_string())? {
                if key.kind == KeyEventKind::Press {
                    handle_key(&mut app, key)?;
                }
            }
        }
        app.maybe_refresh_pending_chat()?;
        app.on_tick()?;
    }

    Ok(())
}

fn handle_key(app: &mut App, key: KeyEvent) -> AppResult<()> {
    match app.input_mode {
        InputMode::Normal => handle_normal_key(app, key),
        InputMode::Search | InputMode::Compose | InputMode::Reply => handle_input_key(app, key),
    }
}

fn handle_normal_key(app: &mut App, key: KeyEvent) -> AppResult<()> {
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
        app.quit = true;
        return Ok(());
    }
    match key.code {
        KeyCode::Char('q') => app.quit = true,
        KeyCode::Tab => app.cycle_focus(),
        KeyCode::Down | KeyCode::Char('j') => {
            app.move_selection_down();
            if app.pane == Pane::Chats {
                app.queue_current_chat_refresh();
            }
        }
        KeyCode::Up | KeyCode::Char('k') => {
            app.move_selection_up();
            if app.pane == Pane::Chats {
                app.queue_current_chat_refresh();
            }
        }
        KeyCode::Enter => match app.pane {
            Pane::Chats => {
                app.refresh_current_chat()?;
                app.status = "Chat refreshed".to_string();
            }
            Pane::Lower if app.lower_view == Some(LowerView::Search) => {
                app.activate_selected_search_result()?;
            }
            Pane::Lower if app.lower_view == Some(LowerView::Outbox) => {
                app.retry_selected_outbox()?;
            }
            _ => {}
        },
        KeyCode::Char('/') => {
            app.input_mode = InputMode::Search;
            app.input.clear();
            app.status = "Search mode".to_string();
        }
        KeyCode::Char('c') => {
            app.input_mode = InputMode::Compose;
            app.input.clear();
            app.status = "Compose to current chat".to_string();
        }
        KeyCode::Char('r') => {
            app.input_mode = InputMode::Reply;
            app.input.clear();
            app.status = "Reply to selected message".to_string();
        }
        KeyCode::Char('o') => {
            if app.lower_view == Some(LowerView::Outbox) {
                app.lower_view = None;
                app.pane = Pane::Chats;
            } else {
                app.refresh_outbox()?;
                app.lower_view = Some(LowerView::Outbox);
                if !app.outbox.is_empty() {
                    app.lower_state.select(Some(0));
                }
                app.pane = Pane::Lower;
            }
        }
        KeyCode::Char('u') => {
            app.unreads_only = !app.unreads_only;
            app.refresh_chats()?;
            app.refresh_current_chat()?;
            app.status = if app.unreads_only {
                "Unread filter enabled".to_string()
            } else {
                "Unread filter disabled".to_string()
            };
        }
        KeyCode::Char('a') => {
            app.refresh_attachments()?;
            if app.attachments.is_empty() {
                app.status = "No attachments in current chat".to_string();
            } else {
                app.lower_view = Some(LowerView::Help);
                app.status = format!("{} attachments in current chat", app.attachments.len());
            }
        }
        KeyCode::Char('R') => {
            app.refresh_all()?;
            app.status = "Refreshed".to_string();
        }
        KeyCode::Char('?') => {
            app.lower_view = if app.lower_view == Some(LowerView::Help) {
                None
            } else {
                Some(LowerView::Help)
            };
            if app.lower_view == Some(LowerView::Help) {
                app.pane = Pane::Lower;
            }
        }
        _ => {}
    }
    Ok(())
}

fn handle_input_key(app: &mut App, key: KeyEvent) -> AppResult<()> {
    match key.code {
        KeyCode::Esc => {
            app.input_mode = InputMode::Normal;
            app.input.clear();
            app.status = "Canceled".to_string();
        }
        KeyCode::Enter => match app.input_mode {
            InputMode::Search => {
                app.run_search()?;
                app.input_mode = InputMode::Normal;
            }
            InputMode::Compose => app.send_input(false)?,
            InputMode::Reply => app.send_input(true)?,
            InputMode::Normal => {}
        },
        KeyCode::Backspace => {
            app.input.pop();
        }
        KeyCode::Char(character) => {
            if !key.modifiers.contains(KeyModifiers::CONTROL) {
                app.input.push(character);
            }
        }
        _ => {}
    }
    Ok(())
}

fn draw(frame: &mut Frame, app: &App) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),
            Constraint::Min(10),
            Constraint::Length(3),
        ])
        .split(frame.area());

    draw_header(frame, layout[0], app);
    draw_body(frame, layout[1], app);
    draw_footer(frame, layout[2], app);
}

fn draw_header(frame: &mut Frame, area: Rect, app: &App) {
    let selected = app
        .selected_chat()
        .map(chat_label)
        .unwrap_or_else(|| "no chat selected".to_string());
    let selected_meta = app
        .selected_chat()
        .map(|chat| {
            let participants = summarize_participants(&chat.participants, 4);
            if participants.is_empty() || participants == selected {
                friendly_timestamp(chat.last_message_at.as_deref())
            } else {
                format!("{} | {}", participants, friendly_timestamp(chat.last_message_at.as_deref()))
            }
        })
        .unwrap_or_else(|| "no conversation loaded".to_string());
    let mode = match app.input_mode {
        InputMode::Normal => "normal",
        InputMode::Search => "search",
        InputMode::Compose => "compose",
        InputMode::Reply => "reply",
    };
    let header = Paragraph::new(vec![
        Line::from(vec![
            Span::styled(" imsg tui ", Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw(" "),
            Span::styled(format!("conversation: {}", selected), Style::default().fg(Color::White)),
            Span::raw(" "),
            Span::styled(
                format!("mode: {}", mode),
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(Span::styled(
            selected_meta,
            Style::default().fg(Color::DarkGray),
        )),
    ]);
    frame.render_widget(header, area);
}

fn draw_body(frame: &mut Frame, area: Rect, app: &App) {
    let horizontal = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(30), Constraint::Percentage(70)])
        .split(area);

    draw_chats(frame, horizontal[0], app);

    if let Some(lower_view) = app.lower_view {
        let right = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Percentage(68), Constraint::Percentage(32)])
            .split(horizontal[1]);
        draw_messages(frame, right[0], app);
        draw_lower(frame, right[1], app, lower_view);
    } else {
        draw_messages(frame, horizontal[1], app);
    }
}

fn draw_chats(frame: &mut Frame, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .chats
        .iter()
        .map(|chat| {
            let title = if chat.unread_count > 0 {
                format!("{}  [{} unread]", chat_label(chat), chat.unread_count)
            } else {
                chat_label(chat)
            };
            let subtitle = chat_subtitle(chat);
            let meta = format!(
                "{} | {} messages",
                friendly_timestamp(chat.last_message_at.as_deref()),
                chat.message_count
            );
            ListItem::new(vec![
                Line::from(Span::styled(
                    compact_string(&title, 44),
                    Style::default().add_modifier(Modifier::BOLD),
                )),
                Line::from(Span::styled(
                    compact_string(&subtitle, 56),
                    Style::default().fg(Color::White),
                )),
                Line::from(Span::styled(meta, Style::default().fg(Color::DarkGray))),
            ])
        })
        .collect();
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Chats"))
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Cyan)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.chats_state.clone();
    frame.render_stateful_widget(list, area, &mut state);
}

fn draw_messages(frame: &mut Frame, area: Rect, app: &App) {
    let title = app
        .selected_chat()
        .map(|chat| format!("Messages: {}", compact_string(&chat_label(chat), 36)))
        .unwrap_or_else(|| "Messages".to_string());
    let items: Vec<ListItem> = app
        .messages
        .iter()
        .map(|message| {
            let actor = message_actor_label(
                message.is_from_me,
                message.handle_display.as_deref(),
                message.handle_id.as_deref(),
            );
            let stamp = friendly_timestamp(message.timestamp.as_deref());
            let mut lines = vec![Line::from(vec![
                Span::styled(
                    stamp,
                    Style::default().fg(Color::DarkGray),
                ),
                Span::raw(" "),
                Span::styled(
                    actor,
                    Style::default()
                        .fg(if message.is_from_me != 0 { Color::Green } else { Color::Yellow })
                        .add_modifier(Modifier::BOLD),
                ),
            ])];
            lines.push(Line::from(Span::styled(
                compact_string(&message.preview, 140),
                Style::default().fg(Color::White),
            )));
            if let Some(parent) = &message.reply_target_preview {
                lines.push(Line::from(Span::styled(
                    format!("↳ {}", compact_string(parent, 100)),
                    Style::default().fg(Color::Blue),
                )));
            }
            if !message.attachments.is_empty() {
                lines.push(Line::from(Span::styled(
                    format!("📎 {} attachment(s)", message.attachments.len()),
                    Style::default().fg(Color::Magenta),
                )));
            }
            ListItem::new(lines)
        })
        .collect();
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title(title))
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Green)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.messages_state.clone();
    frame.render_stateful_widget(list, area, &mut state);
}

fn draw_lower(frame: &mut Frame, area: Rect, app: &App, lower_view: LowerView) {
    match lower_view {
        LowerView::Search => draw_search_results(frame, area, app),
        LowerView::Outbox => draw_outbox(frame, area, app),
        LowerView::Help => draw_help(frame, area, app),
    }
}

fn draw_search_results(frame: &mut Frame, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .search_results
        .iter()
        .map(|row| {
            let actor = message_actor_label(
                row.is_from_me,
                row.handle_display.as_deref(),
                row.handle_id.as_deref(),
            );
            ListItem::new(vec![
                Line::from(Span::styled(
                    compact_string(&row.chat_title, 50),
                    Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
                )),
                Line::from(vec![
                    Span::styled(
                        friendly_timestamp(row.timestamp.as_deref()),
                        Style::default().fg(Color::DarkGray),
                    ),
                    Span::raw(" "),
                    Span::raw(actor),
                    Span::raw(" "),
                    Span::raw(compact_string(&row.preview, 100)),
                ]),
            ])
        })
        .collect();
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Search"))
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.lower_state.clone();
    frame.render_stateful_widget(list, area, &mut state);
}

fn draw_outbox(frame: &mut Frame, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .outbox
        .iter()
        .map(|row| {
            let target = if !row.resolved_recipient.is_empty() {
                row.resolved_recipient.clone()
            } else {
                row.recipient_input.clone().unwrap_or_default()
            };
            let detail = if !row.blocked_reason.is_empty() {
                format!("blocked: {}", row.blocked_reason)
            } else {
                compact_string(&row.provider_detail, 100)
            };
            ListItem::new(vec![
                Line::from(vec![
                    Span::styled(
                        compact_string(&row.status, 12),
                        Style::default()
                            .fg(match row.status.as_str() {
                                "sent" => Color::Green,
                                "blocked" => Color::Red,
                                "failed" => Color::Red,
                                "dry-run" => Color::Blue,
                                _ => Color::Yellow,
                            })
                            .add_modifier(Modifier::BOLD),
                    ),
                    Span::raw(" "),
                    Span::raw(compact_string(&target, 36)),
                ]),
                Line::from(Span::styled(
                    compact_string(&detail, 110),
                    Style::default().fg(Color::DarkGray),
                )),
            ])
        })
        .collect();
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Outbox"))
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Magenta)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.lower_state.clone();
    frame.render_stateful_widget(list, area, &mut state);
}

fn draw_help(frame: &mut Frame, area: Rect, app: &App) {
    let mut lines = vec![
        Line::from("q quit | Tab switch pane | R refresh | / search | c compose | r reply"),
        Line::from("u toggle unreads | o outbox | Enter open/retry | a attachment summary | ? toggle help"),
        Line::from("Esc cancel input | arrows/jk move | current transport stays on imsg over SSH"),
    ];
    if !app.attachments.is_empty() {
        lines.push(Line::from(""));
        lines.push(Line::from(Span::styled(
            "Recent attachments",
            Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
        )));
        for attachment in app.attachments.iter().take(4) {
            let name = if !attachment.transfer_name.is_empty() {
                attachment.transfer_name.clone()
            } else if !attachment.filename.is_empty() {
                attachment.filename.clone()
            } else {
                attachment.attachment_rowid.to_string()
            };
            lines.push(Line::from(compact_string(&name, 100)));
        }
    }
    let paragraph = Paragraph::new(lines)
        .block(Block::default().borders(Borders::ALL).title("Help"))
        .wrap(Wrap { trim: true });
    frame.render_widget(paragraph, area);
}

fn draw_footer(frame: &mut Frame, area: Rect, app: &App) {
    let prompt = match app.input_mode {
        InputMode::Normal => "status",
        InputMode::Search => "search",
        InputMode::Compose => "compose",
        InputMode::Reply => "reply",
    };
    let footer_text = if app.input_mode == InputMode::Normal {
        app.status.clone()
    } else {
        app.input.clone()
    };
    let footer = Paragraph::new(footer_text)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title_alignment(Alignment::Left)
                .title(prompt),
        )
        .wrap(Wrap { trim: false });
    frame.render_widget(footer, area);
    if app.input_mode != InputMode::Normal {
        let x = area.x.saturating_add(1 + app.input.len() as u16);
        let y = area.y.saturating_add(1);
        frame.set_cursor_position((x, y));
    }
}
