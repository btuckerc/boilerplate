use std::io::{self, Stdout};
use std::process::Command;
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread;
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
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph, Wrap};
use ratatui::{Frame, Terminal};
use serde::de::DeserializeOwned;
use serde::de::Error as _;
use serde::Deserialize;
use tui_textarea::TextArea;

type AppResult<T> = Result<T, String>;

const CHAT_LIMIT: usize = 80;
const MESSAGE_LIMIT: usize = 90;
const OUTBOX_LIMIT: usize = 60;
const SEARCH_LIMIT: usize = 60;
const AUTO_SYNC_INTERVAL: Duration = Duration::from_secs(20);
const CHAT_SELECTION_DELAY: Duration = Duration::from_millis(120);
const SEARCH_DEBOUNCE: Duration = Duration::from_millis(180);

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
                _ => Err(D::Error::custom(format!(
                    "unsupported boolish value: {value}"
                ))),
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
enum Focus {
    Chats,
    Messages,
    Composer,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Modal {
    Search,
    Outbox,
    Inspector,
    Help,
}

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

#[derive(Debug, Clone, Deserialize, Default)]
struct MessageRow {
    #[serde(default)]
    message_rowid: i64,
    #[serde(default)]
    date: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    guid: String,
    #[serde(default)]
    handle_id: Option<String>,
    #[serde(default)]
    handle_display: Option<String>,
    #[serde(default)]
    is_from_me: i64,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    text: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    preview: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    kind: String,
    #[serde(default)]
    timestamp: Option<String>,
    #[serde(default)]
    reply_target_guid: Option<String>,
    #[serde(default)]
    reply_target_preview: Option<String>,
    #[serde(default)]
    attachments: Vec<AttachmentRow>,
}

#[derive(Debug, Clone, Deserialize, Default)]
struct ShowResponse {
    chat: ChatSummary,
    #[serde(default)]
    messages: Vec<MessageRow>,
}

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

#[derive(Debug, Clone, Deserialize, Default)]
struct SendResponse {
    #[serde(default, deserialize_with = "deserialize_boolish")]
    ok: bool,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    status: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    detail: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    blocked_reason: String,
    #[serde(default, deserialize_with = "deserialize_stringish")]
    recipient: String,
    #[serde(default)]
    destination_chat_rowid: Option<i64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
struct SyncSummary {
    #[serde(default)]
    source_latest_message_rowid: i64,
    #[serde(default)]
    source_latest_message_at: Option<String>,
    #[serde(default)]
    messages_refreshed: i64,
    #[serde(default)]
    attachments_refreshed: i64,
}

#[derive(Debug, Clone)]
struct QuoteContext {
    message_rowid: i64,
    actor: String,
    preview: String,
}

#[derive(Debug)]
enum BackendEvent {
    Chats {
        request_id: u64,
        result: AppResult<Vec<ChatSummary>>,
    },
    Messages {
        request_id: u64,
        chat_rowid: i64,
        append: bool,
        result: AppResult<ShowResponse>,
    },
    Outbox {
        request_id: u64,
        result: AppResult<Vec<SendJobRow>>,
    },
    Search {
        request_id: u64,
        result: AppResult<Vec<SearchResultRow>>,
    },
    Sync {
        request_id: u64,
        result: AppResult<SyncSummary>,
    },
    Send {
        request_id: u64,
        result: AppResult<SendResponse>,
    },
    Retry {
        request_id: u64,
        result: AppResult<SendResponse>,
    },
}

#[derive(Debug)]
struct App {
    chats: Vec<ChatSummary>,
    chats_state: ListState,
    messages: Vec<MessageRow>,
    messages_state: ListState,
    outbox: Vec<SendJobRow>,
    outbox_state: ListState,
    search_results: Vec<SearchResultRow>,
    search_state: ListState,
    focus: Focus,
    modal: Option<Modal>,
    composer: TextArea<'static>,
    search_input: TextArea<'static>,
    quote_context: Option<QuoteContext>,
    unread_only: bool,
    status: String,
    quit: bool,
    events_tx: Sender<BackendEvent>,
    events_rx: Receiver<BackendEvent>,
    next_request_id: u64,
    chats_request_id: u64,
    messages_request_id: u64,
    outbox_request_id: u64,
    search_request_id: u64,
    sync_request_id: u64,
    send_request_id: u64,
    retry_request_id: u64,
    loaded_chat_rowid: Option<i64>,
    pending_chat_rowid: Option<i64>,
    last_chat_selection_change: Instant,
    sync_inflight: bool,
    send_inflight: bool,
    last_sync_finished_at: Option<Instant>,
    last_sync_summary: Option<SyncSummary>,
    last_sync_error: Option<String>,
    last_tick: Instant,
    search_dirty_at: Option<Instant>,
}

impl App {
    fn new(events_tx: Sender<BackendEvent>, events_rx: Receiver<BackendEvent>) -> Self {
        Self {
            chats: Vec::new(),
            chats_state: ListState::default(),
            messages: Vec::new(),
            messages_state: ListState::default(),
            outbox: Vec::new(),
            outbox_state: ListState::default(),
            search_results: Vec::new(),
            search_state: ListState::default(),
            focus: Focus::Chats,
            modal: None,
            composer: new_textarea(),
            search_input: new_textarea(),
            quote_context: None,
            unread_only: false,
            status: "Loading conversations…".to_string(),
            quit: false,
            events_tx,
            events_rx,
            next_request_id: 1,
            chats_request_id: 0,
            messages_request_id: 0,
            outbox_request_id: 0,
            search_request_id: 0,
            sync_request_id: 0,
            send_request_id: 0,
            retry_request_id: 0,
            loaded_chat_rowid: None,
            pending_chat_rowid: None,
            last_chat_selection_change: Instant::now(),
            sync_inflight: false,
            send_inflight: false,
            last_sync_finished_at: None,
            last_sync_summary: None,
            last_sync_error: None,
            last_tick: Instant::now(),
            search_dirty_at: None,
        }
    }

    fn bootstrap(&mut self) {
        self.refresh_chats();
        self.refresh_outbox();
        self.sync_now(false);
    }

    fn next_request(&mut self) -> u64 {
        let request_id = self.next_request_id;
        self.next_request_id += 1;
        request_id
    }

    fn selected_chat(&self) -> Option<&ChatSummary> {
        self.chats_state
            .selected()
            .and_then(|idx| self.chats.get(idx))
    }

    fn selected_chat_rowid(&self) -> Option<i64> {
        self.selected_chat().map(|chat| chat.chat_rowid)
    }

    fn selected_message(&self) -> Option<&MessageRow> {
        self.messages_state
            .selected()
            .and_then(|idx| self.messages.get(idx))
    }

    fn selected_outbox(&self) -> Option<&SendJobRow> {
        self.outbox_state
            .selected()
            .and_then(|idx| self.outbox.get(idx))
    }

    fn selected_search_result(&self) -> Option<&SearchResultRow> {
        self.search_state
            .selected()
            .and_then(|idx| self.search_results.get(idx))
    }

    fn focus_next(&mut self) {
        if self.modal.is_some() {
            return;
        }
        self.focus = match self.focus {
            Focus::Chats => Focus::Messages,
            Focus::Messages => Focus::Composer,
            Focus::Composer => Focus::Chats,
        };
    }

    fn refresh_chats(&mut self) {
        let request_id = self.next_request();
        self.chats_request_id = request_id;
        self.status = if self.unread_only {
            "Refreshing unread conversations…".to_string()
        } else {
            "Refreshing conversations…".to_string()
        };
        spawn_chats_request(self.events_tx.clone(), request_id, self.unread_only);
    }

    fn refresh_outbox(&mut self) {
        let request_id = self.next_request();
        self.outbox_request_id = request_id;
        spawn_outbox_request(self.events_tx.clone(), request_id);
    }

    fn refresh_current_chat(&mut self, append: bool, before: Option<(i64, i64)>) {
        let Some(chat_rowid) = self.selected_chat_rowid() else {
            self.loaded_chat_rowid = None;
            self.messages.clear();
            self.messages_state.select(None);
            return;
        };
        let request_id = self.next_request();
        self.messages_request_id = request_id;
        if !append {
            self.status = format!("Loading {}", chat_label(self.selected_chat().unwrap()));
        }
        spawn_messages_request(
            self.events_tx.clone(),
            request_id,
            chat_rowid,
            append,
            before,
        );
    }

    fn sync_now(&mut self, manual: bool) {
        if self.sync_inflight {
            return;
        }
        let request_id = self.next_request();
        self.sync_request_id = request_id;
        self.sync_inflight = true;
        if manual {
            self.status = "Syncing index…".to_string();
        }
        spawn_sync_request(self.events_tx.clone(), request_id);
    }

    fn mark_search_dirty(&mut self) {
        self.search_dirty_at = Some(Instant::now());
    }

    fn open_search(&mut self) {
        self.modal = Some(Modal::Search);
        self.search_state.select(Some(0));
        self.mark_search_dirty();
        self.status = "Search conversations".to_string();
    }

    fn close_modal(&mut self) {
        self.modal = None;
        self.search_dirty_at = None;
    }

    fn toggle_help(&mut self) {
        if self.modal == Some(Modal::Help) {
            self.close_modal();
        } else {
            self.modal = Some(Modal::Help);
        }
    }

    fn toggle_outbox(&mut self) {
        if self.modal == Some(Modal::Outbox) {
            self.close_modal();
        } else {
            self.modal = Some(Modal::Outbox);
            self.refresh_outbox();
            if !self.outbox.is_empty() {
                self.outbox_state.select(Some(0));
            }
        }
    }

    fn toggle_inspector(&mut self) {
        if self.modal == Some(Modal::Inspector) {
            self.close_modal();
        } else {
            self.modal = Some(Modal::Inspector);
        }
    }

    fn queue_current_chat_refresh(&mut self) {
        self.pending_chat_rowid = self.selected_chat_rowid();
        self.last_chat_selection_change = Instant::now();
    }

    fn maybe_request_pending_chat(&mut self) {
        let Some(chat_rowid) = self.pending_chat_rowid else {
            return;
        };
        if self.last_chat_selection_change.elapsed() < CHAT_SELECTION_DELAY {
            return;
        }
        if self.loaded_chat_rowid == Some(chat_rowid) {
            self.pending_chat_rowid = None;
            return;
        }
        self.pending_chat_rowid = None;
        self.refresh_current_chat(false, None);
    }

    fn maybe_run_search(&mut self) {
        if self.modal != Some(Modal::Search) {
            return;
        }
        let Some(started) = self.search_dirty_at else {
            return;
        };
        if started.elapsed() < SEARCH_DEBOUNCE {
            return;
        }
        self.search_dirty_at = None;
        let query = textarea_text(&self.search_input).trim().to_string();
        if query.is_empty() {
            self.search_results.clear();
            self.search_state.select(None);
            return;
        }
        let request_id = self.next_request();
        self.search_request_id = request_id;
        self.status = format!("Searching for {}", query);
        spawn_search_request(self.events_tx.clone(), request_id, query);
    }

    fn maybe_auto_sync(&mut self) {
        if self.sync_inflight {
            return;
        }
        if let Some(last_sync) = self.last_sync_finished_at {
            if last_sync.elapsed() < AUTO_SYNC_INTERVAL {
                return;
            }
        }
        self.sync_now(false);
    }

    fn process_events(&mut self) {
        while let Ok(event) = self.events_rx.try_recv() {
            match event {
                BackendEvent::Chats { request_id, result } => {
                    if request_id != self.chats_request_id {
                        continue;
                    }
                    match result {
                        Ok(chats) => {
                            let previous_chat_rowid = self.selected_chat_rowid();
                            self.chats = chats;
                            if self.chats.is_empty() {
                                self.chats_state.select(None);
                                self.messages.clear();
                                self.messages_state.select(None);
                                self.loaded_chat_rowid = None;
                            } else {
                                let idx = previous_chat_rowid
                                    .and_then(|chat_rowid| {
                                        self.chats
                                            .iter()
                                            .position(|chat| chat.chat_rowid == chat_rowid)
                                    })
                                    .unwrap_or(0)
                                    .min(self.chats.len() - 1);
                                self.chats_state.select(Some(idx));
                                if self.loaded_chat_rowid != self.selected_chat_rowid() {
                                    self.refresh_current_chat(false, None);
                                }
                            }
                        }
                        Err(error) => self.status = error,
                    }
                }
                BackendEvent::Messages {
                    request_id,
                    chat_rowid,
                    append,
                    result,
                } => {
                    if request_id != self.messages_request_id {
                        continue;
                    }
                    match result {
                        Ok(response) => {
                            if self.selected_chat_rowid() != Some(chat_rowid) {
                                continue;
                            }
                            if append {
                                if response.messages.is_empty() {
                                    self.status = "Start of conversation".to_string();
                                } else {
                                    let loaded_count = response.messages.len();
                                    let mut merged = response.messages;
                                    merged.extend(self.messages.drain(..));
                                    self.messages = merged;
                                    self.messages_state
                                        .select(Some(loaded_count.saturating_sub(1)));
                                    self.status =
                                        format!("Loaded {} older messages", loaded_count);
                                }
                            } else {
                                let previous_message_rowid = self
                                    .selected_message()
                                    .map(|message| message.message_rowid);
                                self.messages = response.messages;
                                if self.messages.is_empty() {
                                    self.messages_state.select(None);
                                } else {
                                    let idx = previous_message_rowid
                                        .and_then(|message_rowid| {
                                            self.messages
                                                .iter()
                                                .position(|message| {
                                                    message.message_rowid == message_rowid
                                                })
                                        })
                                        .unwrap_or(self.messages.len().saturating_sub(1))
                                        .min(self.messages.len() - 1);
                                    self.messages_state.select(Some(idx));
                                }
                            }
                            self.loaded_chat_rowid = Some(chat_rowid);
                        }
                        Err(error) => self.status = error,
                    }
                }
                BackendEvent::Outbox { request_id, result } => {
                    if request_id != self.outbox_request_id {
                        continue;
                    }
                    match result {
                        Ok(rows) => {
                            let previous_job = self.selected_outbox().map(|job| job.job_rowid);
                            self.outbox = rows;
                            if self.outbox.is_empty() {
                                self.outbox_state.select(None);
                            } else {
                                let idx = previous_job
                                    .and_then(|job_rowid| {
                                        self.outbox
                                            .iter()
                                            .position(|job| job.job_rowid == job_rowid)
                                    })
                                    .unwrap_or(0)
                                    .min(self.outbox.len() - 1);
                                self.outbox_state.select(Some(idx));
                            }
                        }
                        Err(error) => self.status = error,
                    }
                }
                BackendEvent::Search { request_id, result } => {
                    if request_id != self.search_request_id {
                        continue;
                    }
                    match result {
                        Ok(rows) => {
                            self.search_results = rows;
                            if self.search_results.is_empty() {
                                self.search_state.select(None);
                            } else {
                                self.search_state.select(Some(0));
                            }
                        }
                        Err(error) => self.status = error,
                    }
                }
                BackendEvent::Sync { request_id, result } => {
                    if request_id != self.sync_request_id {
                        continue;
                    }
                    self.sync_inflight = false;
                    self.last_sync_finished_at = Some(Instant::now());
                    match result {
                        Ok(summary) => {
                            self.last_sync_error = None;
                            self.last_sync_summary = Some(summary);
                            self.refresh_chats();
                            self.refresh_outbox();
                            if self.selected_chat_rowid().is_some() {
                                self.refresh_current_chat(false, None);
                            }
                        }
                        Err(error) => {
                            self.last_sync_error = Some(error.clone());
                            self.status = error;
                        }
                    }
                }
                BackendEvent::Send { request_id, result } => {
                    if request_id != self.send_request_id {
                        continue;
                    }
                    self.send_inflight = false;
                    match result {
                        Ok(response) => {
                            self.status = if response.ok {
                                if response.recipient.trim().is_empty() {
                                    "Message sent".to_string()
                                } else {
                                    format!("Sent to {}", response.recipient)
                                }
                            } else if !response.detail.trim().is_empty() {
                                response.detail
                            } else {
                                response.status
                            };
                            self.refresh_outbox();
                            self.refresh_chats();
                            if self.selected_chat_rowid().is_some() {
                                self.refresh_current_chat(false, None);
                            }
                        }
                        Err(error) => {
                            self.status = error;
                        }
                    }
                }
                BackendEvent::Retry { request_id, result } => {
                    if request_id != self.retry_request_id {
                        continue;
                    }
                    match result {
                        Ok(response) => {
                            self.status = if response.ok {
                                "Retry sent".to_string()
                            } else if !response.detail.trim().is_empty() {
                                response.detail
                            } else {
                                response.status
                            };
                            self.refresh_outbox();
                            self.refresh_chats();
                            if self.selected_chat_rowid().is_some() {
                                self.refresh_current_chat(false, None);
                            }
                        }
                        Err(error) => self.status = error,
                    }
                }
            }
        }
    }

    fn move_chat_selection(&mut self, delta: isize) {
        move_list_state(&mut self.chats_state, self.chats.len(), delta);
        self.queue_current_chat_refresh();
    }

    fn move_message_selection(&mut self, delta: isize) {
        move_list_state(&mut self.messages_state, self.messages.len(), delta);
    }

    fn move_outbox_selection(&mut self, delta: isize) {
        move_list_state(&mut self.outbox_state, self.outbox.len(), delta);
    }

    fn move_search_selection(&mut self, delta: isize) {
        move_list_state(&mut self.search_state, self.search_results.len(), delta);
    }

    fn load_older_messages(&mut self) {
        let Some(oldest) = self.messages.first() else {
            self.refresh_current_chat(false, None);
            return;
        };
        self.refresh_current_chat(true, Some((oldest.date, oldest.message_rowid)));
    }

    fn jump_to_search_result(&mut self) {
        let Some(result) = self.selected_search_result().cloned() else {
            return;
        };
        if let Some(position) = self
            .chats
            .iter()
            .position(|chat| chat.chat_rowid == result.chat_rowid)
        {
            self.chats_state.select(Some(position));
            self.focus = Focus::Messages;
            self.close_modal();
            self.refresh_current_chat(false, None);
            self.status = format!("Opened {}", result.chat_title);
        } else {
            self.status = "Search hit points to a chat outside the current list".to_string();
        }
    }

    fn pin_selected_message_for_context(&mut self) {
        let Some(message) = self.selected_message() else {
            self.status = "No message selected".to_string();
            return;
        };
        self.quote_context = Some(QuoteContext {
            message_rowid: message.message_rowid,
            actor: message_actor_label(
                message.is_from_me,
                message.handle_display.as_deref(),
                message.handle_id.as_deref(),
            ),
            preview: compact_string(&message_body(message), 120),
        });
        self.focus = Focus::Composer;
        self.status = "Pinned selected message for compose context".to_string();
    }

    fn clear_compose_context(&mut self) {
        self.quote_context = None;
    }

    fn send_composer(&mut self) {
        let Some(chat_rowid) = self.selected_chat_rowid() else {
            self.status = "No chat selected".to_string();
            return;
        };
        let text = textarea_text(&self.composer).trim().to_string();
        if text.is_empty() {
            self.status = "Message cannot be empty".to_string();
            return;
        }
        let request_id = self.next_request();
        self.send_request_id = request_id;
        self.send_inflight = true;
        spawn_send_request(self.events_tx.clone(), request_id, chat_rowid, text);
        self.composer = new_textarea();
        self.clear_compose_context();
        self.focus = Focus::Messages;
        self.status = "Dispatching message…".to_string();
    }

    fn retry_selected_outbox(&mut self) {
        let Some(job_rowid) = self.selected_outbox().map(|job| job.job_rowid) else {
            self.status = "No outbox job selected".to_string();
            return;
        };
        let request_id = self.next_request();
        self.retry_request_id = request_id;
        spawn_retry_request(self.events_tx.clone(), request_id, job_rowid);
        self.status = format!("Retrying job {}", job_rowid);
    }

    fn sync_status_label(&self) -> String {
        if self.sync_inflight {
            return "syncing".to_string();
        }
        if let Some(error) = &self.last_sync_error {
            return format!("sync error: {}", compact_string(error, 48));
        }
        if let Some(summary) = &self.last_sync_summary {
            let age = self
                .last_sync_finished_at
                .map(|instant| format_duration(instant.elapsed()))
                .unwrap_or_else(|| "unknown".to_string());
            return format!(
                "synced {} ago | {} rows",
                age,
                summary.messages_refreshed
            );
        }
        "sync idle".to_string()
    }
}

fn new_textarea() -> TextArea<'static> {
    let mut textarea = TextArea::default();
    textarea.set_cursor_line_style(Style::default());
    textarea
}

fn spawn_chats_request(tx: Sender<BackendEvent>, request_id: u64, unread_only: bool) {
    thread::spawn(move || {
        let args = if unread_only {
            vec![
                "unreads".to_string(),
                "--limit".to_string(),
                CHAT_LIMIT.to_string(),
                "--no-sync".to_string(),
                "--json".to_string(),
            ]
        } else {
            vec![
                "chats".to_string(),
                "--limit".to_string(),
                CHAT_LIMIT.to_string(),
                "--no-sync".to_string(),
                "--json".to_string(),
            ]
        };
        let result = run_imsg_json::<Vec<ChatSummary>>(&args);
        let _ = tx.send(BackendEvent::Chats { request_id, result });
    });
}

fn spawn_messages_request(
    tx: Sender<BackendEvent>,
    request_id: u64,
    chat_rowid: i64,
    append: bool,
    before: Option<(i64, i64)>,
) {
    thread::spawn(move || {
        let mut args = vec![
            "show".to_string(),
            chat_rowid.to_string(),
            "--limit".to_string(),
            MESSAGE_LIMIT.to_string(),
        ];
        if let Some((before_date, before_rowid)) = before {
            args.push("--before-date".to_string());
            args.push(before_date.to_string());
            args.push("--before-rowid".to_string());
            args.push(before_rowid.to_string());
        }
        args.push("--no-sync".to_string());
        args.push("--json".to_string());
        let result = run_imsg_json::<ShowResponse>(&args);
        let _ = tx.send(BackendEvent::Messages {
            request_id,
            chat_rowid,
            append,
            result,
        });
    });
}

fn spawn_outbox_request(tx: Sender<BackendEvent>, request_id: u64) {
    thread::spawn(move || {
        let args = vec![
            "outbox".to_string(),
            "--limit".to_string(),
            OUTBOX_LIMIT.to_string(),
            "--no-sync".to_string(),
            "--json".to_string(),
        ];
        let result = run_imsg_json::<Vec<SendJobRow>>(&args);
        let _ = tx.send(BackendEvent::Outbox { request_id, result });
    });
}

fn spawn_search_request(tx: Sender<BackendEvent>, request_id: u64, query: String) {
    thread::spawn(move || {
        let args = vec![
            "search".to_string(),
            query,
            "--limit".to_string(),
            SEARCH_LIMIT.to_string(),
            "--no-sync".to_string(),
            "--json".to_string(),
        ];
        let result = run_imsg_json::<Vec<SearchResultRow>>(&args);
        let _ = tx.send(BackendEvent::Search { request_id, result });
    });
}

fn spawn_sync_request(tx: Sender<BackendEvent>, request_id: u64) {
    thread::spawn(move || {
        let args = vec!["sync".to_string(), "--quiet".to_string(), "--json".to_string()];
        let result = run_imsg_json::<SyncSummary>(&args);
        let _ = tx.send(BackendEvent::Sync { request_id, result });
    });
}

fn spawn_send_request(tx: Sender<BackendEvent>, request_id: u64, chat_rowid: i64, text: String) {
    thread::spawn(move || {
        let args = vec![
            "send".to_string(),
            "--chat".to_string(),
            chat_rowid.to_string(),
            "--text".to_string(),
            text,
            "--json".to_string(),
        ];
        let result = run_imsg_json::<SendResponse>(&args);
        let _ = tx.send(BackendEvent::Send { request_id, result });
    });
}

fn spawn_retry_request(tx: Sender<BackendEvent>, request_id: u64, job_rowid: i64) {
    thread::spawn(move || {
        let args = vec![
            "retry".to_string(),
            job_rowid.to_string(),
            "--json".to_string(),
        ];
        let result = run_imsg_json::<SendResponse>(&args);
        let _ = tx.send(BackendEvent::Retry { request_id, result });
    });
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

fn textarea_text(textarea: &TextArea<'_>) -> String {
    textarea.lines().join("\n")
}

fn format_duration(duration: Duration) -> String {
    let seconds = duration.as_secs();
    if seconds < 60 {
        return format!("{}s", seconds);
    }
    if seconds < 3600 {
        return format!("{}m", seconds / 60);
    }
    format!("{}h", seconds / 3600)
}

fn message_body(message: &MessageRow) -> String {
    let text = message.text.trim();
    if !text.is_empty() {
        return text.to_string();
    }
    let preview = message.preview.trim();
    if !preview.is_empty() {
        return preview.to_string();
    }
    "[empty message]".to_string()
}

fn message_kind_label(kind: &str) -> Option<(&'static str, Color)> {
    match kind {
        "reply" => Some(("reply", Color::Blue)),
        "reaction" => Some(("reaction", Color::Magenta)),
        "system" => Some(("system", Color::Cyan)),
        "retracted" => Some(("retracted", Color::Red)),
        _ => None,
    }
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

fn message_actor_label(
    is_from_me: i64,
    handle_display: Option<&str>,
    handle_id: Option<&str>,
) -> String {
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
    let preview = compact_string(&chat.last_message_preview, 90);
    if !preview.is_empty() && preview != "[empty]" {
        return preview;
    }
    let participants = summarize_participants(&chat.participants, 4);
    if !participants.is_empty() && participants != chat_label(chat) {
        return participants;
    }
    "No recent preview".to_string()
}

fn wrap_lines(value: &str, width: usize, max_lines: usize) -> Vec<String> {
    if width == 0 {
        return Vec::new();
    }
    let mut lines = Vec::new();
    let mut current = String::new();
    for word in value.split_whitespace() {
        let candidate = if current.is_empty() {
            word.to_string()
        } else {
            format!("{} {}", current, word)
        };
        if visual_width(&candidate) > width && !current.is_empty() {
            lines.push(current);
            current = word.to_string();
            if lines.len() >= max_lines {
                break;
            }
        } else {
            current = candidate;
        }
    }
    if lines.len() < max_lines && !current.is_empty() {
        lines.push(current);
    }
    if lines.len() > max_lines {
        lines.truncate(max_lines);
    }
    if lines.len() == max_lines {
        if let Some(last) = lines.last_mut() {
            if visual_width(last) > width.saturating_sub(3) {
                *last = compact_string(last, width);
            }
        }
    }
    lines
}

fn visual_width(value: &str) -> usize {
    value.chars().count()
}

fn centered_rect(area: Rect, width_pct: u16, height_pct: u16) -> Rect {
    let vertical = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - height_pct) / 2),
            Constraint::Percentage(height_pct),
            Constraint::Percentage((100 - height_pct) / 2),
        ])
        .split(area);
    let horizontal = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - width_pct) / 2),
            Constraint::Percentage(width_pct),
            Constraint::Percentage((100 - width_pct) / 2),
        ])
        .split(vertical[1]);
    horizontal[1]
}

fn run_imsg_json<T: DeserializeOwned>(args: &[String]) -> AppResult<T> {
    let output = Command::new("imsg")
        .args(args)
        .output()
        .map_err(|error| format!("failed to run imsg: {error}"))?;
    if !output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        let detail = if !stdout.trim().is_empty() {
            stdout
        } else {
            stderr
        };
        return Err(detail.trim().to_string());
    }
    serde_json::from_slice::<T>(&output.stdout)
        .map_err(|error| format!("failed to decode imsg json: {error}"))
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
    let (events_tx, events_rx) = mpsc::channel::<BackendEvent>();
    let mut app = App::new(events_tx, events_rx);
    app.bootstrap();

    loop {
        app.process_events();
        app.maybe_request_pending_chat();
        app.maybe_run_search();
        if app.last_tick.elapsed() >= Duration::from_millis(250) {
            app.maybe_auto_sync();
            app.last_tick = Instant::now();
        }

        terminal
            .draw(|frame| draw(frame, &app))
            .map_err(|error| error.to_string())?;

        if app.quit {
            break;
        }

        if event::poll(Duration::from_millis(100)).map_err(|error| error.to_string())? {
            if let Event::Key(key) = event::read().map_err(|error| error.to_string())? {
                if key.kind == KeyEventKind::Press {
                    handle_key(&mut app, key);
                }
            }
        }
    }

    Ok(())
}

fn handle_key(app: &mut App, key: KeyEvent) {
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
        app.quit = true;
        return;
    }

    if let Some(modal) = app.modal {
        match modal {
            Modal::Search => handle_search_key(app, key),
            Modal::Outbox => handle_outbox_key(app, key),
            Modal::Inspector => handle_inspector_key(app, key),
            Modal::Help => handle_help_key(app, key),
        }
        return;
    }

    match key.code {
        KeyCode::Char('q') => app.quit = true,
        KeyCode::Tab => app.focus_next(),
        KeyCode::Char('/') => app.open_search(),
        KeyCode::Char('o') => app.toggle_outbox(),
        KeyCode::Char('?') => app.toggle_help(),
        KeyCode::Char('i') => app.toggle_inspector(),
        KeyCode::Char('u') => {
            app.unread_only = !app.unread_only;
            app.refresh_chats();
            app.status = if app.unread_only {
                "Unread filter enabled".to_string()
            } else {
                "Unread filter disabled".to_string()
            };
        }
        KeyCode::Char('R') => app.sync_now(true),
        KeyCode::Char('c') => app.focus = Focus::Composer,
        KeyCode::Char('r') => app.pin_selected_message_for_context(),
        _ => match app.focus {
            Focus::Chats => handle_chats_key(app, key),
            Focus::Messages => handle_messages_key(app, key),
            Focus::Composer => handle_composer_key(app, key),
        },
    }
}

fn handle_chats_key(app: &mut App, key: KeyEvent) {
    match key.code {
        KeyCode::Down | KeyCode::Char('j') => app.move_chat_selection(1),
        KeyCode::Up | KeyCode::Char('k') => app.move_chat_selection(-1),
        KeyCode::PageDown => app.move_chat_selection(10),
        KeyCode::PageUp => app.move_chat_selection(-10),
        KeyCode::Home | KeyCode::Char('g') => {
            if !app.chats.is_empty() {
                app.chats_state.select(Some(0));
                app.queue_current_chat_refresh();
            }
        }
        KeyCode::End | KeyCode::Char('G') => {
            if !app.chats.is_empty() {
                app.chats_state.select(Some(app.chats.len() - 1));
                app.queue_current_chat_refresh();
            }
        }
        KeyCode::Enter | KeyCode::Right | KeyCode::Char('l') => app.focus = Focus::Messages,
        _ => {}
    }
}

fn handle_messages_key(app: &mut App, key: KeyEvent) {
    match key.code {
        KeyCode::Down | KeyCode::Char('j') => app.move_message_selection(1),
        KeyCode::Up | KeyCode::Char('k') => {
            if app.messages_state.selected().unwrap_or(0) == 0 {
                app.load_older_messages();
            } else {
                app.move_message_selection(-1);
            }
        }
        KeyCode::PageDown => app.move_message_selection(8),
        KeyCode::PageUp => {
            if app.messages_state.selected().unwrap_or(0) <= 7 {
                app.load_older_messages();
            } else {
                app.move_message_selection(-8);
            }
        }
        KeyCode::Home | KeyCode::Char('g') => {
            if !app.messages.is_empty() {
                app.messages_state.select(Some(0));
            }
        }
        KeyCode::End | KeyCode::Char('G') => {
            if !app.messages.is_empty() {
                app.messages_state.select(Some(app.messages.len() - 1));
            }
        }
        KeyCode::Left | KeyCode::Char('h') | KeyCode::Esc => app.focus = Focus::Chats,
        _ => {}
    }
}

fn handle_composer_key(app: &mut App, key: KeyEvent) {
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('s') {
        app.send_composer();
        return;
    }
    if key.code == KeyCode::Esc {
        app.focus = Focus::Messages;
        return;
    }
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('x') {
        app.composer = new_textarea();
        app.clear_compose_context();
        app.status = "Cleared composer".to_string();
        return;
    }
    app.composer.input(key);
}

fn handle_search_key(app: &mut App, key: KeyEvent) {
    match key.code {
        KeyCode::Esc => app.close_modal(),
        KeyCode::Enter => app.jump_to_search_result(),
        KeyCode::Down | KeyCode::Char('j') => app.move_search_selection(1),
        KeyCode::Up | KeyCode::Char('k') => app.move_search_selection(-1),
        KeyCode::PageDown => app.move_search_selection(8),
        KeyCode::PageUp => app.move_search_selection(-8),
        KeyCode::Char('?') => {}
        _ => {
            app.search_input.input(key);
            app.mark_search_dirty();
        }
    }
}

fn handle_outbox_key(app: &mut App, key: KeyEvent) {
    match key.code {
        KeyCode::Esc | KeyCode::Char('o') => app.close_modal(),
        KeyCode::Enter | KeyCode::Char('r') => app.retry_selected_outbox(),
        KeyCode::Down | KeyCode::Char('j') => app.move_outbox_selection(1),
        KeyCode::Up | KeyCode::Char('k') => app.move_outbox_selection(-1),
        KeyCode::PageDown => app.move_outbox_selection(8),
        KeyCode::PageUp => app.move_outbox_selection(-8),
        KeyCode::Home | KeyCode::Char('g') => {
            if !app.outbox.is_empty() {
                app.outbox_state.select(Some(0));
            }
        }
        KeyCode::End | KeyCode::Char('G') => {
            if !app.outbox.is_empty() {
                app.outbox_state.select(Some(app.outbox.len() - 1));
            }
        }
        _ => {}
    }
}

fn handle_inspector_key(app: &mut App, key: KeyEvent) {
    if matches!(key.code, KeyCode::Esc | KeyCode::Char('i')) {
        app.close_modal();
    }
}

fn handle_help_key(app: &mut App, key: KeyEvent) {
    if matches!(key.code, KeyCode::Esc | KeyCode::Char('?')) {
        app.close_modal();
    }
}

fn draw(frame: &mut Frame, app: &App) {
    let compose_lines = textarea_text(&app.composer).lines().count().max(1);
    let compose_height = (compose_lines as u16).clamp(3, 5) + 2;
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),
            Constraint::Min(8),
            Constraint::Length(compose_height),
            Constraint::Length(2),
        ])
        .split(frame.area());

    draw_header(frame, layout[0], app);
    draw_body(frame, layout[1], app);
    draw_composer(frame, layout[2], app);
    draw_footer(frame, layout[3], app);

    match app.modal {
        Some(Modal::Search) => draw_search_popup(frame, app),
        Some(Modal::Outbox) => draw_outbox_popup(frame, app),
        Some(Modal::Inspector) => draw_inspector_popup(frame, app),
        Some(Modal::Help) => draw_help_popup(frame, app),
        None => {}
    }
}

fn draw_header(frame: &mut Frame, area: Rect, app: &App) {
    let selected = app
        .selected_chat()
        .map(chat_label)
        .unwrap_or_else(|| "no chat selected".to_string());
    let meta = app
        .selected_chat()
        .map(|chat| {
            let participants = summarize_participants(&chat.participants, 4);
            if participants.is_empty() || participants == selected {
                friendly_timestamp(chat.last_message_at.as_deref())
            } else {
                format!(
                    "{} | {}",
                    participants,
                    friendly_timestamp(chat.last_message_at.as_deref())
                )
            }
        })
        .unwrap_or_else(|| "no conversation loaded".to_string());
    let unread = if app.unread_only { "unreads" } else { "all chats" };
    let header = Paragraph::new(vec![
        Line::from(vec![
            Span::styled(
                " imsg ",
                Style::default()
                    .fg(Color::Black)
                    .bg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::raw(" "),
            Span::styled(
                compact_string(&selected, 44),
                Style::default().fg(Color::White).add_modifier(Modifier::BOLD),
            ),
            Span::raw(" "),
            Span::styled(
                format!("| {} | {}", unread, app.sync_status_label()),
                Style::default().fg(Color::DarkGray),
            ),
        ]),
        Line::from(Span::styled(meta, Style::default().fg(Color::DarkGray))),
    ]);
    frame.render_widget(header, area);
}

fn draw_body(frame: &mut Frame, area: Rect, app: &App) {
    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(32), Constraint::Percentage(68)])
        .split(area);
    draw_chats(frame, columns[0], app);
    draw_messages(frame, columns[1], app);
}

fn draw_chats(frame: &mut Frame, area: Rect, app: &App) {
    let items: Vec<ListItem> = app
        .chats
        .iter()
        .map(|chat| {
            let title = if chat.unread_count > 0 {
                format!("{}  [{}]", chat_label(chat), chat.unread_count)
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
                    compact_string(&subtitle, 58),
                    Style::default().fg(Color::White),
                )),
                Line::from(Span::styled(meta, Style::default().fg(Color::DarkGray))),
            ])
        })
        .collect();
    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Chats")
                .border_style(if app.focus == Focus::Chats {
                    Style::default().fg(Color::Cyan)
                } else {
                    Style::default().fg(Color::DarkGray)
                }),
        )
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
        .map(|chat| format!("Messages: {}", compact_string(&chat_label(chat), 40)))
        .unwrap_or_else(|| "Messages".to_string());
    let inner_width = area.width.saturating_sub(4) as usize;
    let preview_width = inner_width.saturating_sub(2);
    let items: Vec<ListItem> = app
        .messages
        .iter()
        .map(|message| {
            let actor = message_actor_label(
                message.is_from_me,
                message.handle_display.as_deref(),
                message.handle_id.as_deref(),
            );
            let mut header_spans = vec![
                Span::styled(
                    friendly_timestamp(message.timestamp.as_deref()),
                    Style::default().fg(Color::DarkGray),
                ),
                Span::raw(" "),
                Span::styled(
                    actor,
                    Style::default()
                        .fg(if message.is_from_me != 0 {
                            Color::Green
                        } else {
                            Color::Yellow
                        })
                        .add_modifier(Modifier::BOLD),
                ),
            ];
            if let Some((label, color)) = message_kind_label(&message.kind) {
                header_spans.push(Span::raw(" "));
                header_spans.push(Span::styled(
                    format!("[{}]", label),
                    Style::default().fg(color).add_modifier(Modifier::BOLD),
                ));
            }

            let mut lines = vec![Line::from(header_spans)];
            for line in wrap_lines(&message_body(message), preview_width, 3) {
                lines.push(Line::from(Span::raw(line)));
            }
            if let Some(reply_preview) = &message.reply_target_preview {
                lines.push(Line::from(Span::styled(
                    format!("in reply to {}", compact_string(reply_preview, preview_width)),
                    Style::default().fg(Color::Blue),
                )));
            }
            if !message.attachments.is_empty() {
                lines.push(Line::from(Span::styled(
                    format!("{} attachment(s)", message.attachments.len()),
                    Style::default().fg(Color::Magenta),
                )));
            }
            ListItem::new(lines)
        })
        .collect();
    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title(title)
                .border_style(if app.focus == Focus::Messages {
                    Style::default().fg(Color::Green)
                } else {
                    Style::default().fg(Color::DarkGray)
                }),
        )
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Green)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.messages_state.clone();
    frame.render_stateful_widget(list, area, &mut state);
}

fn draw_composer(frame: &mut Frame, area: Rect, app: &App) {
    let block = Block::default()
        .borders(Borders::ALL)
        .title(if app.focus == Focus::Composer {
            "Compose [Ctrl+S send | Ctrl+X clear | Esc blur]"
        } else {
            "Compose"
        })
        .border_style(if app.focus == Focus::Composer {
            Style::default().fg(Color::Yellow)
        } else {
            Style::default().fg(Color::DarkGray)
        });
    let inner = block.inner(area);
    frame.render_widget(block, area);

    let sections = if app.quote_context.is_some() {
        Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(1), Constraint::Min(1)])
            .split(inner)
    } else {
        Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Min(1)])
            .split(inner)
    };

    if let Some(context) = &app.quote_context {
        let label = format!(
            "Context {}: {}",
            context.message_rowid,
            compact_string(
                &format!("{} | {}", context.actor, context.preview),
                inner.width.saturating_sub(2) as usize
            )
        );
        let paragraph =
            Paragraph::new(Line::from(Span::styled(label, Style::default().fg(Color::Blue))));
        frame.render_widget(paragraph, sections[0]);
    }

    let editor_area = *sections.last().unwrap_or(&inner);
    frame.render_widget(&app.composer, editor_area);
    if app.focus == Focus::Composer {
        let (cursor_x, cursor_y) = app.composer.cursor();
        frame.set_cursor_position((
            editor_area.x.saturating_add(cursor_x as u16),
            editor_area.y.saturating_add(cursor_y as u16),
        ));
    }
}

fn draw_footer(frame: &mut Frame, area: Rect, app: &App) {
    let hints = "Tab cycle | / search | o outbox | i inspect | u unread filter | r pin context | R sync | q quit";
    let footer = Paragraph::new(vec![
        Line::from(Span::raw(compact_string(
            &app.status,
            area.width.saturating_sub(2) as usize,
        ))),
        Line::from(Span::styled(
            compact_string(hints, area.width.saturating_sub(2) as usize),
            Style::default().fg(Color::DarkGray),
        )),
    ])
    .alignment(Alignment::Left)
    .wrap(Wrap { trim: true });
    frame.render_widget(footer, area);
}

fn draw_search_popup(frame: &mut Frame, app: &App) {
    let area = centered_rect(frame.area(), 76, 68);
    frame.render_widget(Clear, area);
    let sections = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(6)])
        .split(area);

    let search_block = Block::default()
        .borders(Borders::ALL)
        .title("Search")
        .border_style(Style::default().fg(Color::Yellow));
    let search_inner = search_block.inner(sections[0]);
    frame.render_widget(search_block, sections[0]);
    frame.render_widget(&app.search_input, search_inner);
    let (cursor_x, cursor_y) = app.search_input.cursor();
    frame.set_cursor_position((
        search_inner.x.saturating_add(cursor_x as u16),
        search_inner.y.saturating_add(cursor_y as u16),
    ));

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
                    compact_string(&row.chat_title, 60),
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
                    Span::raw(compact_string(&row.preview, 120)),
                ]),
            ])
        })
        .collect();
    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Results [Enter opens]")
                .border_style(Style::default().fg(Color::DarkGray)),
        )
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.search_state.clone();
    frame.render_stateful_widget(list, sections[1], &mut state);
}

fn draw_outbox_popup(frame: &mut Frame, app: &App) {
    let area = centered_rect(frame.area(), 72, 62);
    frame.render_widget(Clear, area);
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
                compact_string(&row.provider_detail, 120)
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
                                "queued" => Color::Yellow,
                                "sending" => Color::Yellow,
                                _ => Color::White,
                            })
                            .add_modifier(Modifier::BOLD),
                    ),
                    Span::raw(" "),
                    Span::raw(compact_string(&target, 42)),
                    Span::raw(" "),
                    Span::styled(
                        friendly_timestamp(row.created_at.as_deref()),
                        Style::default().fg(Color::DarkGray),
                    ),
                ]),
                Line::from(Span::styled(
                    compact_string(&detail, 120),
                    Style::default().fg(Color::DarkGray),
                )),
                Line::from(Span::raw(compact_string(&row.message_text, 120))),
            ])
        })
        .collect();
    let list = List::new(items)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Outbox [Enter retries]")
                .border_style(Style::default().fg(Color::Magenta)),
        )
        .highlight_style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::Magenta)
                .add_modifier(Modifier::BOLD),
        );
    let mut state = app.outbox_state.clone();
    frame.render_stateful_widget(list, area, &mut state);
}

fn draw_inspector_popup(frame: &mut Frame, app: &App) {
    let area = centered_rect(frame.area(), 70, 60);
    frame.render_widget(Clear, area);
    let Some(message) = app.selected_message() else {
        let paragraph = Paragraph::new("No message selected")
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .title("Message Inspector"),
            )
            .wrap(Wrap { trim: true });
        frame.render_widget(paragraph, area);
        return;
    };
    let actor = message_actor_label(
        message.is_from_me,
        message.handle_display.as_deref(),
        message.handle_id.as_deref(),
    );
    let mut lines = vec![Line::from(vec![
        Span::styled(
            friendly_timestamp(message.timestamp.as_deref()),
            Style::default().fg(Color::DarkGray),
        ),
        Span::raw(" "),
        Span::styled(
            actor,
            Style::default()
                .fg(if message.is_from_me != 0 {
                    Color::Green
                } else {
                    Color::Yellow
                })
                .add_modifier(Modifier::BOLD),
        ),
    ])];
    if let Some((label, color)) = message_kind_label(&message.kind) {
        lines[0].spans.push(Span::raw(" "));
        lines[0].spans.push(Span::styled(
            format!("[{}]", label),
            Style::default().fg(color).add_modifier(Modifier::BOLD),
        ));
    }
    lines.push(Line::from(""));
    for body_line in message_body(message).lines() {
        lines.push(Line::from(body_line.to_string()));
    }
    if let Some(reply_preview) = &message.reply_target_preview {
        lines.push(Line::from(""));
        lines.push(Line::from(Span::styled(
            "In reply to",
            Style::default().fg(Color::Blue).add_modifier(Modifier::BOLD),
        )));
        lines.push(Line::from(reply_preview.to_string()));
    }
    if !message.attachments.is_empty() {
        lines.push(Line::from(""));
        lines.push(Line::from(Span::styled(
            format!("Attachments ({})", message.attachments.len()),
            Style::default()
                .fg(Color::Magenta)
                .add_modifier(Modifier::BOLD),
        )));
        for attachment in &message.attachments {
            let attachment_name = if !attachment.transfer_name.trim().is_empty() {
                attachment.transfer_name.trim().to_string()
            } else if !attachment.filename.trim().is_empty() {
                attachment.filename.trim().to_string()
            } else {
                format!("attachment {}", attachment.attachment_rowid)
            };
            lines.push(Line::from(compact_string(&attachment_name, 180)));
        }
    }
    let paragraph = Paragraph::new(lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .title("Message Inspector"),
        )
        .wrap(Wrap { trim: true });
    frame.render_widget(paragraph, area);
}

fn draw_help_popup(frame: &mut Frame, app: &App) {
    let area = centered_rect(frame.area(), 70, 54);
    frame.render_widget(Clear, area);
    let lines = vec![
        Line::from("Chats and messages are always visible. Moving in the chat list reloads the transcript after a short debounce."),
        Line::from("Tab cycles chats, transcript, and composer."),
        Line::from("The composer is multiline. Enter inserts a newline. Ctrl+S sends."),
        Line::from("Press r to pin the selected message as compose context without pretending it is a native threaded reply."),
        Line::from("/ opens live search. Typing updates results. Enter opens the selected hit."),
        Line::from("o opens the outbox. Enter retries the selected job."),
        Line::from("u toggles unread-only chat filtering. R runs a fresh sync."),
        Line::from("i shows the full selected message. q exits."),
        Line::from(""),
        Line::from(Span::styled(
            format!("Current sync: {}", app.sync_status_label()),
            Style::default().fg(Color::DarkGray),
        )),
    ];
    let paragraph = Paragraph::new(lines)
        .block(Block::default().borders(Borders::ALL).title("Help"))
        .wrap(Wrap { trim: true });
    frame.render_widget(paragraph, area);
}
