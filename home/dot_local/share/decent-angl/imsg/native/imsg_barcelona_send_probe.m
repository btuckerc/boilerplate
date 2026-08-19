#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>

static NSString *Describe(id value) {
    if (!value) {
        return @"";
    }
    @try {
        return [[value description] copy] ?: @"";
    } @catch (__unused NSException *exc) {
        return @"";
    }
}

static NSString *ArgValue(NSArray<NSString *> *args, NSString *flag, NSString *fallback) {
    NSUInteger index = [args indexOfObject:flag];
    if (index == NSNotFound || index + 1 >= [args count]) {
        return fallback;
    }
    return args[index + 1];
}

static BOOL HasFlag(NSArray<NSString *> *args, NSString *flag) {
    return [args containsObject:flag];
}

static id Call0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return nil;
    }
    return ((id(*)(id, SEL))objc_msgSend)(target, sel);
}

static id Call1(id target, NSString *name, id arg) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return nil;
    }
    return ((id(*)(id, SEL, id))objc_msgSend)(target, sel, arg);
}

static void CallVoid0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL))objc_msgSend)(target, sel);
}

static void CallVoid1(id target, NSString *name, id arg) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, id))objc_msgSend)(target, sel, arg);
}

static void CallVoidULL1(id target, NSString *name, unsigned long long value) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, unsigned long long))objc_msgSend)(target, sel, value);
}

static BOOL CallBool0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return NO;
    }
    return ((BOOL(*)(id, SEL))objc_msgSend)(target, sel);
}

static NSString *StringProp(id target, NSString *name) {
    id value = Call0(target, name);
    return [value isKindOfClass:[NSString class]] ? value : Describe(value);
}

static void RunLoopSleep(NSTimeInterval seconds) {
    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:seconds]];
}

@interface ProbeListener : NSObject
@property(nonatomic) BOOL didCompleteSetup;
@property(nonatomic) BOOL didLoadChats;
@property(nonatomic, copy) NSString *lastSentGUID;
@end

@implementation ProbeListener

- (void)setupComplete {
    self.didCompleteSetup = YES;
}

- (void)setupComplete:(BOOL)success info:(NSDictionary *)info {
    self.didCompleteSetup = success;
    (void)info;
}

- (void)loadedChats:(NSArray *)chats {
    self.didLoadChats = [chats count] > 0;
}

- (void)loadedChats:(NSArray *)chats queryID:(NSString *)queryID {
    self.didLoadChats = [chats count] > 0 || [queryID length] > 0;
}

- (void)account:(NSString *)accountUniqueID
           chat:(NSString *)chatIdentifier
          style:(unsigned char)chatStyle
 chatProperties:(NSDictionary *)properties
notifySentMessage:(id)message
       sendTime:(NSNumber *)sendTime {
    self.lastSentGUID = StringProp(message, @"guid");
    (void)accountUniqueID;
    (void)chatIdentifier;
    (void)chatStyle;
    (void)properties;
    (void)sendTime;
}

@end

static id BestHandleForID(NSString *identifier) {
    id accountController = Call0(NSClassFromString(@"IMAccountController"), @"sharedInstance");
    id activeIMessageAccount = Call0(accountController, @"activeIMessageAccount");
    if (!activeIMessageAccount) {
        NSArray *accounts = Call0(accountController, @"accounts");
        if ([accounts isKindOfClass:[NSArray class]]) {
            for (id account in accounts) {
                NSString *serviceName = StringProp(account, @"serviceName");
                if ([serviceName isEqualToString:@"iMessage"]) {
                    activeIMessageAccount = account;
                    break;
                }
            }
        }
    }
    if (activeIMessageAccount) {
        id handle = Call1(activeIMessageAccount, @"imHandleWithID:", identifier);
        if (handle) {
            return handle;
        }
    }
    id registry = Call0(NSClassFromString(@"IMHandleRegistrar"), @"sharedInstance");
    id handles = Call1(registry, @"getIMHandlesForID:", identifier);
    if ([handles isKindOfClass:[NSArray class]] && [handles count] > 0) {
        return [handles firstObject];
    }
    return nil;
}

static id CreateMessage(NSString *text, NSString *threadIdentifier) {
    Class messageClass = NSClassFromString(@"IMMessage");
    if (!messageClass) {
        return nil;
    }
    NSAttributedString *body = [[NSAttributedString alloc] initWithString:text ?: @""];
    SEL sel = NSSelectorFromString(@"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:");
    if ([messageClass respondsToSelector:sel]) {
        return ((id(*)(id, SEL, id, id, id, unsigned long long, id))objc_msgSend)(
            messageClass,
            sel,
            body,
            nil,
            @[],
            0x100005ULL,
            threadIdentifier
        );
    }

    id raw = [messageClass new];
    SEL initSel = NSSelectorFromString(@"initWithSender:time:text:messageSubject:fileTransferGUIDs:flags:error:guid:subject:balloonBundleID:payloadData:expressiveSendStyleID:");
    if (!raw || !initSel || ![raw respondsToSelector:initSel]) {
        return nil;
    }
    id message = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id, id, id, id))objc_msgSend)(
        raw,
        initSel,
        nil,
        nil,
        body,
        nil,
        @[],
        0x100005ULL,
        nil,
        nil,
        nil,
        nil,
        nil,
        nil
    );
    if (threadIdentifier.length) {
        CallVoid1(message, @"setThreadIdentifier:", threadIdentifier);
    }
    return message;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *chatGuid = ArgValue(args, @"--chat-guid", @"any;-;btuckercraig@gmail.com");
        NSString *handleID = ArgValue(args, @"--handle", @"btuckercraig@gmail.com");
        NSString *replyGUID = ArgValue(args, @"--reply-guid", @"");
        NSString *text = ArgValue(args, @"--text", @"");
        BOOL send = HasFlag(args, @"--send");
        unsigned int listenerCapabilities = 2162567U;

        [NSApplication sharedApplication];
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDPersistence.framework/IMDPersistence", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMFoundation.framework/IMFoundation", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMSharedUtilities.framework/IMSharedUtilities", RTLD_LAZY);
        NSMutableDictionary *payload = [NSMutableDictionary dictionary];
        payload[@"chat_guid"] = chatGuid;
        payload[@"handle"] = handleID;
        payload[@"reply_guid"] = replyGUID ?: @"";
        payload[@"send"] = @(send);

        id daemon = Call0(NSClassFromString(@"IMDaemonController"), @"sharedInstance");
        if (!daemon) {
            daemon = Call0(NSClassFromString(@"IMDaemonController"), @"sharedController");
        }
        payload[@"daemon"] = Describe(daemon);

        ProbeListener *listener = [ProbeListener new];
        id daemonListener = Call0(daemon, @"listener");
        payload[@"daemon_listener"] = Describe(daemonListener);
        if (daemonListener && [daemonListener respondsToSelector:NSSelectorFromString(@"addHandler:")]) {
            ((void(*)(id, SEL, id))objc_msgSend)(daemonListener, NSSelectorFromString(@"addHandler:"), listener);
            payload[@"handler_added"] = @YES;
        } else {
            payload[@"handler_added"] = @NO;
        }

        if ([daemon respondsToSelector:NSSelectorFromString(@"addListenerID:capabilities:")]) {
            ((void(*)(id, SEL, id, unsigned int))objc_msgSend)(daemon, NSSelectorFromString(@"addListenerID:capabilities:"), @"com.decentangl.imsg.barcelona-probe", listenerCapabilities);
            payload[@"listener_capabilities"] = @(listenerCapabilities);
        }

        if ([daemon respondsToSelector:NSSelectorFromString(@"blockUntilConnected")]) {
            CallVoid0(daemon, @"blockUntilConnected");
            payload[@"used_block_until_connected"] = @YES;
        } else if ([daemon respondsToSelector:NSSelectorFromString(@"connectToDaemonWithLaunch:capabilities:blockUntilConnected:")]) {
            BOOL launch = YES;
            BOOL block = YES;
            ((void(*)(id, SEL, BOOL, unsigned int, BOOL))objc_msgSend)(
                daemon,
                NSSelectorFromString(@"connectToDaemonWithLaunch:capabilities:blockUntilConnected:"),
                launch,
                listenerCapabilities,
                block
            );
            payload[@"used_block_until_connected"] = @NO;
        }

        RunLoopSleep(1.0);
        if (@available(macOS 12.0, *)) {
            CallVoid0(daemon, @"loadAllChats");
        } else {
            CallVoid1(daemon, @"loadChatsWithChatID:", @"all");
        }
        RunLoopSleep(3.0);

        id accountController = Call0(NSClassFromString(@"IMAccountController"), @"sharedInstance");
        NSArray *accounts = Call0(accountController, @"accounts");
        payload[@"accounts_count"] = @([accounts isKindOfClass:[NSArray class]] ? [accounts count] : 0);
        payload[@"accounts"] = Describe(accounts);
        payload[@"active_imessage_account"] = Describe(Call0(accountController, @"activeIMessageAccount"));

        if ([accounts isKindOfClass:[NSArray class]]) {
            for (id account in accounts) {
                CallVoidULL1(account, @"updateCapabilities:", ULLONG_MAX);
            }
            RunLoopSleep(0.5);
        }

        id registry = Call0(NSClassFromString(@"IMChatRegistry"), @"sharedInstance");
        payload[@"registry"] = Describe(registry);
        id chat = Call1(registry, @"existingChatWithGUID:", chatGuid);
        if (!chat) {
            id handle = BestHandleForID(handleID);
            payload[@"resolved_handle"] = Describe(handle);
            chat = Call1(registry, @"chatForIMHandle:", handle);
        }

        payload[@"chat"] = Describe(chat);
        payload[@"chat_can_send"] = @(CallBool0(chat, @"canSend"));
        payload[@"chat_account"] = Describe(Call0(chat, @"account"));
        payload[@"chat_has_had_successful_query"] = @(CallBool0(chat, @"hasHadSuccessfulQuery"));

        NSString *threadIdentifier = @"";
        payload[@"thread_identifier"] = threadIdentifier ?: @"";

        if (send && chat && text.length) {
            id message = CreateMessage(text, threadIdentifier.length ? threadIdentifier : nil);
            payload[@"message_before_send"] = Describe(message);
            if ([chat respondsToSelector:NSSelectorFromString(@"sendMessage:")]) {
                ((void(*)(id, SEL, id))objc_msgSend)(chat, NSSelectorFromString(@"sendMessage:"), message);
                payload[@"send_selector"] = @"sendMessage:";
            }
            RunLoopSleep(4.0);
            payload[@"message_after_send"] = Describe(message);
            payload[@"chat_last_message"] = Describe(Call0(chat, @"lastMessage"));
            payload[@"chat_last_sent_message"] = Describe(Call0(chat, @"lastSentMessage"));
            payload[@"listener_last_sent_guid"] = listener.lastSentGUID ?: @"";
        }

        payload[@"setup_complete"] = @(listener.didCompleteSetup);
        payload[@"loaded_chats"] = @(listener.didLoadChats);

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
