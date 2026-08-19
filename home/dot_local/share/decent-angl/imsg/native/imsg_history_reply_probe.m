#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>

typedef id (*ThreadIdentifierFn)(id);
static void *gIMCoreHandle = NULL;
static void *gIMDaemonCoreHandle = NULL;

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

static unsigned long long ArgULL(NSArray<NSString *> *args, NSString *flag, unsigned long long fallback) {
    NSString *value = ArgValue(args, flag, nil);
    if (!value.length) {
        return fallback;
    }
    return (unsigned long long)strtoull([value UTF8String], NULL, 10);
}

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

static unsigned long long CallULL0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return 0;
    }
    return ((unsigned long long(*)(id, SEL))objc_msgSend)(target, sel);
}

static unsigned int CallUInt0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return 0;
    }
    return ((unsigned int(*)(id, SEL))objc_msgSend)(target, sel);
}

static BOOL InvokeDaemonConnect(id daemon, unsigned long long capabilities, NSMutableDictionary *payload) {
    SEL detailedSel = NSSelectorFromString(@"connectToDaemonWithLaunch:capabilities:blockUntilConnected:");
    if (daemon && detailedSel && [daemon respondsToSelector:detailedSel]) {
        @try {
            NSMethodSignature *signature = [daemon methodSignatureForSelector:detailedSel];
            NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
            [invocation setTarget:daemon];
            [invocation setSelector:detailedSel];
            BOOL launch = YES;
            BOOL block = YES;
            [invocation setArgument:&launch atIndex:2];
            const char *capsType = [signature getArgumentTypeAtIndex:3];
            if (capsType && capsType[0] == 'Q') {
                [invocation setArgument:&capabilities atIndex:3];
            } else {
                unsigned int caps32 = (unsigned int)capabilities;
                [invocation setArgument:&caps32 atIndex:3];
            }
            [invocation setArgument:&block atIndex:4];
            [invocation invoke];
            BOOL result = NO;
            [invocation getReturnValue:&result];
            payload[@"daemon_connect_selector"] = @"connectToDaemonWithLaunch:capabilities:blockUntilConnected:";
            return result;
        } @catch (NSException *exc) {
            payload[@"daemon_connect_exception"] = Describe(exc);
            return NO;
        }
    }

    SEL connectSel = NSSelectorFromString(@"connectToDaemon");
    if (daemon && connectSel && [daemon respondsToSelector:connectSel]) {
        payload[@"daemon_connect_selector"] = @"connectToDaemon";
        return ((BOOL(*)(id, SEL))objc_msgSend)(daemon, connectSel);
    }
    return NO;
}

static id ConfigureDaemonContext(id daemon, unsigned long long capabilities, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"multiplexedConnectionWithLabel:capabilities:context:");
    if (!daemon || !sel || ![daemon respondsToSelector:sel]) {
        return nil;
    }
    NSString *bundleID = [[NSBundle mainBundle] bundleIdentifier] ?: @"com.decentangl.imsg-native-probe";
    NSString *processName = [[NSProcessInfo processInfo] processName];
    NSDictionary *context = @{
        @"bundleIdentifier": bundleID,
        @"bundleID": bundleID,
        @"processName": processName ?: @"",
        @"executablePath": [[NSProcessInfo processInfo] arguments].firstObject ?: @"",
    };
    @try {
        NSMethodSignature *signature = [daemon methodSignatureForSelector:sel];
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:daemon];
        [invocation setSelector:sel];
        id label = bundleID;
        id contextArg = context;
        [invocation setArgument:&label atIndex:2];
        const char *capsType = [signature getArgumentTypeAtIndex:3];
        if (capsType && capsType[0] == 'Q') {
            [invocation setArgument:&capabilities atIndex:3];
        } else {
            unsigned int caps32 = (unsigned int)capabilities;
            [invocation setArgument:&caps32 atIndex:3];
        }
        [invocation setArgument:&contextArg atIndex:4];
        [invocation invoke];
        __unsafe_unretained id connection = nil;
        [invocation getReturnValue:&connection];
        payload[@"daemon_custom_context"] = Describe(context);
        payload[@"daemon_custom_connection"] = Describe(connection);
        if (connection) {
            CallVoid1(daemon, @"setAnonymousMultiplexedConnection:", connection);
        }
        return connection;
    } @catch (NSException *exc) {
        payload[@"daemon_custom_connection_exception"] = Describe(exc);
        return nil;
    }
}

static NSString *StringProp(id target, NSString *name) {
    id value = Call0(target, name);
    if ([value isKindOfClass:[NSString class]]) {
        return value;
    }
    return Describe(value);
}

static NSDictionary *DumpMessage(id message) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!message) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([message class]) ?: @"";
    payload[@"description"] = Describe(message);
    payload[@"guid"] = StringProp(message, @"guid") ?: @"";
    payload[@"threadIdentifier"] = StringProp(message, @"threadIdentifier") ?: @"";
    payload[@"replyToGUID"] = StringProp(message, @"replyToGUID") ?: @"";
    payload[@"text"] = Describe(Call0(message, @"text")) ?: @"";
    payload[@"plainBody"] = StringProp(message, @"plainBody") ?: @"";
    id originator = Call0(message, @"threadOriginator");
    payload[@"threadOriginator"] = Describe(originator);
    payload[@"threadOriginatorGUID"] = StringProp(originator, @"guid") ?: @"";
    payload[@"messageSummaryInfo"] = Describe(Call0(message, @"messageSummaryInfo")) ?: @"";
    payload[@"_imMessageItem"] = Describe(Call0(message, @"_imMessageItem")) ?: @"";
    return payload;
}

static id MessageLikeFromItem(id item) {
    if (!item) {
        return nil;
    }
    return Call0(item, @"message") ?: item;
}

static NSDictionary *DumpChatItem(id item) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!item) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([item class]) ?: @"";
    payload[@"description"] = Describe(item);
    payload[@"guid"] = StringProp(Call0(item, @"_item"), @"guid") ?: @"";
    payload[@"index"] = Describe(Call0(item, @"index")) ?: @"";
    payload[@"range"] = Describe(Call0(item, @"messagePartRange")) ?: @"";
    payload[@"text"] = Describe(Call0(item, @"text")) ?: @"";
    return payload;
}

static NSDictionary *DumpChat(id chat) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!chat) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([chat class]) ?: @"";
    payload[@"description"] = Describe(chat);
    payload[@"guid"] = StringProp(chat, @"guid") ?: @"";
    payload[@"chatIdentifier"] = StringProp(chat, @"chatIdentifier") ?: @"";
    payload[@"roomName"] = StringProp(chat, @"roomName") ?: @"";
    payload[@"account"] = Describe(Call0(chat, @"account")) ?: @"";
    payload[@"service"] = Describe(Call0(chat, @"service")) ?: @"";
    payload[@"lastMessage"] = Describe(Call0(chat, @"lastMessage")) ?: @"";
    return payload;
}

static id LoadMessageByGUID(NSString *guid, NSMutableDictionary *payload) {
    id store = Call0(NSClassFromString(@"IMDMessageStore"), @"sharedInstance");
    payload[@"message_store"] = Describe(store);
    if (store && guid.length) {
        id message = Call1(store, @"messageWithGUID:", guid);
        payload[@"message_store_messageWithGUID"] = Describe(message);
        if (message) {
            payload[@"history_selector"] = @"IMDMessageStore messageWithGUID:";
            return message;
        }
        id item = Call1(store, @"itemWithGUID:", guid);
        payload[@"message_store_itemWithGUID"] = Describe(item);
        if (item) {
            payload[@"history_selector"] = @"IMDMessageStore itemWithGUID:";
            id itemMessage = Call0(item, @"message");
            payload[@"message_store_item_message"] = Describe(itemMessage);
            if (itemMessage) {
                return itemMessage;
            }
            payload[@"history_loaded_non_message"] = Describe(item);
            return item;
        }
    }
    return nil;
}

static id FirstPartChatItem(id messageItem) {
    id parts = Call0(messageItem, @"messageParts");
    if ([parts isKindOfClass:[NSArray class]] && [(NSArray *)parts count] > 0) {
        return [(NSArray *)parts firstObject];
    }
    id items = Call0(messageItem, @"_newChatItems");
    if ([items isKindOfClass:[NSArray class]]) {
        for (id item in (NSArray *)items) {
            id itemGuid = Call0(Call0(item, @"_item"), @"guid");
            if (itemGuid) {
                return item;
            }
        }
        return [(NSArray *)items firstObject];
    }
    return items;
}

static id StoreItemQuery(id store, NSArray *handles, NSArray *services, NSString *guid, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"itemsWithHandles:onServices:messageGUID:limit:");
    if (!store || !sel || ![store respondsToSelector:sel]) {
        return nil;
    }
    @try {
        NSMethodSignature *signature = [store methodSignatureForSelector:sel];
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:store];
        [invocation setSelector:sel];
        id handlesArg = handles;
        id servicesArg = services;
        id guidArg = guid;
        NSInteger limit = 20;
        [invocation setArgument:&handlesArg atIndex:2];
        [invocation setArgument:&servicesArg atIndex:3];
        [invocation setArgument:&guidArg atIndex:4];
        [invocation setArgument:&limit atIndex:5];
        [invocation invoke];
        __unsafe_unretained id result = nil;
        [invocation getReturnValue:&result];
        payload[@"message_store_itemsWithHandles"] = Describe(result);
        if ([result isKindOfClass:[NSArray class]]) {
            for (id item in (NSArray *)result) {
                if ([StringProp(item, @"guid") isEqualToString:guid]) {
                    payload[@"message_store_item_query_hit"] = Describe(item);
                    return item;
                }
            }
            return [(NSArray *)result firstObject];
        }
    } @catch (NSException *exc) {
        payload[@"message_store_itemsWithHandles_exception"] = Describe(exc);
    }
    return nil;
}

static NSString *DeriveThreadIdentifier(id message, id partItem, NSMutableDictionary *payload) {
    NSString *threadIdentifier = StringProp(message, @"threadIdentifier");
    if (threadIdentifier.length) {
        payload[@"thread_source"] = @"message.threadIdentifier";
        return threadIdentifier;
    }
    NSString *partThreadIdentifier = StringProp(partItem, @"threadIdentifier");
    if (partThreadIdentifier.length) {
        payload[@"thread_source"] = @"partItem.threadIdentifier";
        return partThreadIdentifier;
    }
    void *symbol = dlsym(gIMCoreHandle ? gIMCoreHandle : RTLD_DEFAULT, "IMCreateThreadIdentifierForMessagePartChatItem");
    if (!symbol || !partItem) {
        payload[@"thread_source"] = @"missing_thread_identifier_function";
        return @"";
    }
    ThreadIdentifierFn fn = (ThreadIdentifierFn)symbol;
    @try {
        id generated = fn(partItem);
        payload[@"thread_source"] = @"IMCreateThreadIdentifierForMessagePartChatItem";
        return [generated isKindOfClass:[NSString class]] ? generated : Describe(generated);
    } @catch (NSException *exc) {
        payload[@"thread_identifier_exception"] = Describe(exc);
        return @"";
    }
}

static id FindChat(NSString *chatGuid, NSString *messageGuid, NSMutableDictionary *payload) {
    id store = Call0(NSClassFromString(@"IMDMessageStore"), @"sharedInstance");
    if (store && messageGuid.length) {
        id storeChat = Call1(store, @"chatForMessageGUID:", messageGuid);
        if (storeChat) {
            payload[@"chat_selector"] = @"IMDMessageStore chatForMessageGUID:";
            return storeChat;
        }
    }
    id registry = Call0(NSClassFromString(@"IMChatRegistry"), @"sharedInstance");
    payload[@"chat_registry"] = Describe(registry);
    if (!registry) {
        return nil;
    }
    NSArray<NSString *> *selectors = @[
        @"existingChatWithGUID:",
        @"existingChatWithChatIdentifier:",
    ];
    for (NSString *selectorName in selectors) {
        id chat = Call1(registry, selectorName, chatGuid);
        if (chat) {
            payload[@"chat_selector"] = selectorName;
            return chat;
        }
    }
    return nil;
}

static id BuildMessage(NSString *text, NSString *threadIdentifier, NSMutableDictionary *payload) {
    Class messageClass = NSClassFromString(@"IMMessage");
    if (!messageClass) {
        payload[@"build_error"] = @"IMMessage class missing";
        return nil;
    }
    NSAttributedString *body = [[NSAttributedString alloc] initWithString:text ?: @""];

    SEL initSel = NSSelectorFromString(@"initWithSender:time:text:messageSubject:fileTransferGUIDs:flags:error:guid:subject:balloonBundleID:payloadData:expressiveSendStyleID:threadIdentifier:");
    if ([[messageClass alloc] respondsToSelector:initSel]) {
        unsigned long long flags = 100005ULL;
        id message = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id, id, id, id, id))objc_msgSend)(
            [messageClass alloc],
            initSel,
            nil,
            nil,
            body,
            nil,
            nil,
            flags,
            nil,
            nil,
            nil,
            nil,
            nil,
            nil,
            threadIdentifier.length ? threadIdentifier : nil
        );
        payload[@"build_selector"] = @"initWithSender:time:text:messageSubject:fileTransferGUIDs:flags:error:guid:subject:balloonBundleID:payloadData:expressiveSendStyleID:threadIdentifier:";
        return message;
    }

    SEL classSel = NSSelectorFromString(@"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:");
    if ([messageClass respondsToSelector:classSel]) {
        unsigned long long flags = 100005ULL;
        id message = ((id(*)(id, SEL, id, id, id, unsigned long long, id))objc_msgSend)(
            messageClass,
            classSel,
            body,
            nil,
            nil,
            flags,
            threadIdentifier.length ? threadIdentifier : nil
        );
        payload[@"build_selector"] = @"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:";
        return message;
    }

    payload[@"build_error"] = @"no IMMessage constructor";
    return nil;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *messageGuid = ArgValue(args, @"--message-guid", @"");
        NSString *chatGuid = ArgValue(args, @"--chat-guid", @"");
        NSString *identifier = ArgValue(args, @"--identifier", @"btuckercraig@gmail.com");
        NSString *serviceName = ArgValue(args, @"--service", @"iMessage");
        NSString *text = ArgValue(args, @"--text", @"");
        NSString *outPath = ArgValue(args, @"--out", @"");
        unsigned long long capabilities = ArgULL(args, @"--capabilities", 4485895ULL);
        BOOL send = HasFlag(args, @"--send");

        fprintf(stderr, "probe:start\n");
        fflush(stderr);
        [NSApplication sharedApplication];
        gIMCoreHandle = dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY | RTLD_GLOBAL);
        gIMDaemonCoreHandle = dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY | RTLD_GLOBAL);
        fprintf(stderr, "probe:frameworks\n");
        fflush(stderr);

        NSMutableDictionary *payload = [NSMutableDictionary dictionary];
        payload[@"message_guid"] = messageGuid ?: @"";
        payload[@"chat_guid"] = chatGuid ?: @"";
        payload[@"identifier"] = identifier ?: @"";
        payload[@"service_name"] = serviceName ?: @"";
        payload[@"text"] = text ?: @"";
        payload[@"send"] = @(send);
        payload[@"requested_capabilities"] = @(capabilities);

        id daemon = Call0(NSClassFromString(@"IMDaemonController"), @"sharedController");
        if (!daemon) {
            daemon = Call0(NSClassFromString(@"IMDaemonController"), @"sharedInstance");
        }
        payload[@"daemon"] = Describe(daemon);
        payload[@"daemon_process_context"] = Describe(Call0(daemon, @"processContext")) ?: @"";
        payload[@"daemon_listener_id"] = StringProp(daemon, @"listenerID") ?: @"";
        payload[@"daemon_capabilities_before"] = @(CallUInt0(daemon, @"capabilities"));
        payload[@"daemon_process_capabilities_before"] = @(CallULL0(daemon, @"processCapabilities"));
        SEL setCapsSel = NSSelectorFromString(@"setProcessCapabilities:");
        if (daemon && setCapsSel && [daemon respondsToSelector:setCapsSel]) {
            ((void(*)(id, SEL, unsigned long long))objc_msgSend)(daemon, setCapsSel, capabilities);
        }
        payload[@"daemon_process_capabilities_after"] = @(CallULL0(daemon, @"processCapabilities"));
        payload[@"daemon_capabilities_after"] = @(CallUInt0(daemon, @"capabilities"));
        ConfigureDaemonContext(daemon, capabilities, payload);
        payload[@"daemon_process_context_after_custom_connection"] = Describe(Call0(daemon, @"processContext")) ?: @"";
        BOOL connected = InvokeDaemonConnect(daemon, capabilities, payload);
        payload[@"daemon_connect_result"] = @(connected);

        id message = LoadMessageByGUID(messageGuid, payload);
        if (!message) {
            id store = Call0(NSClassFromString(@"IMDMessageStore"), @"sharedInstance");
            id queriedItem = StoreItemQuery(
                store,
                identifier.length ? @[identifier] : @[],
                serviceName.length ? @[serviceName] : @[],
                messageGuid,
                payload
            );
            message = MessageLikeFromItem(queriedItem);
            if (queriedItem && !payload[@"history_selector"]) {
                payload[@"history_selector"] = @"IMDMessageStore itemsWithHandles:onServices:messageGUID:limit:";
            }
        }
        fprintf(stderr, "probe:message=%s\n", [Describe(message) UTF8String]);
        fflush(stderr);
        payload[@"message"] = DumpMessage(message);

        id messageItem = Call0(message, @"_imMessageItem");
        id partItem = FirstPartChatItem(messageItem);
        payload[@"message_item"] = Describe(messageItem);
        payload[@"part_item"] = DumpChatItem(partItem);

        NSString *threadIdentifier = DeriveThreadIdentifier(message, partItem, payload);
        payload[@"derived_thread_identifier"] = threadIdentifier ?: @"";

        id chat = FindChat(chatGuid, messageGuid, payload);
        fprintf(stderr, "probe:chat=%s\n", [Describe(chat) UTF8String]);
        fflush(stderr);
        payload[@"chat"] = DumpChat(chat);

        if (send && chat && threadIdentifier.length && text.length) {
            id outgoing = BuildMessage(text, threadIdentifier, payload);
            payload[@"outgoing"] = DumpMessage(outgoing);
            @try {
                SEL sendSel = NSSelectorFromString(@"sendMessage:");
                if (sendSel && [chat respondsToSelector:sendSel]) {
                    ((void(*)(id, SEL, id))objc_msgSend)(chat, sendSel, outgoing);
                    payload[@"send_selector"] = @"sendMessage:";
                    payload[@"send_invoked"] = @YES;
                }
            } @catch (NSException *exc) {
                payload[@"send_exception"] = Describe(exc);
            }
            for (NSInteger index = 0; index < 60; index += 1) {
                [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
            }
        }

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        if (outPath.length) {
            [json writeToFile:outPath atomically:YES];
        }
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
