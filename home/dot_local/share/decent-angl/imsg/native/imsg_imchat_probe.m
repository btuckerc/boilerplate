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

static unsigned long long ArgULL(NSArray<NSString *> *args, NSString *flag, unsigned long long fallback) {
    NSString *value = ArgValue(args, flag, nil);
    if (!value.length) {
        return fallback;
    }
    return (unsigned long long)strtoull([value UTF8String], NULL, 10);
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

static id SafeCall1(id target, NSString *name, id arg, NSMutableDictionary *payload, NSString *keyPrefix) {
    @try {
        return Call1(target, name, arg);
    } @catch (NSException *exc) {
        if (payload && keyPrefix) {
            payload[[NSString stringWithFormat:@"%@_exception", keyPrefix]] = Describe(exc);
        }
        return nil;
    }
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

static unsigned long long CallULL0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return 0;
    }
    return ((unsigned long long(*)(id, SEL))objc_msgSend)(target, sel);
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

static BOOL InvokeLoadMessagesUpToGUID(id chat, NSString *guid, NSInteger limit, NSMutableDictionary *payload) {
    NSArray<NSString *> *selectors = @[
        @"loadMessagesUpToGUID:date:limit:loadImmediately:",
        @"loadMessagesUpToGUID:limit:",
    ];
    for (NSString *selectorName in selectors) {
        SEL sel = NSSelectorFromString(selectorName);
        if (!chat || !sel || ![chat respondsToSelector:sel]) {
            continue;
        }
        @try {
            NSMethodSignature *signature = [chat methodSignatureForSelector:sel];
            if (!signature) {
                continue;
            }
            NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
            [invocation setTarget:chat];
            [invocation setSelector:sel];
            id guidArg = guid;
            [invocation setArgument:&guidArg atIndex:2];
            if ([selectorName isEqualToString:@"loadMessagesUpToGUID:date:limit:loadImmediately:"]) {
                id dateArg = nil;
                NSInteger limitArg = limit;
                BOOL loadImmediately = YES;
                [invocation setArgument:&dateArg atIndex:3];
                [invocation setArgument:&limitArg atIndex:4];
                [invocation setArgument:&loadImmediately atIndex:5];
            } else {
                NSInteger limitArg = limit;
                [invocation setArgument:&limitArg atIndex:3];
            }
            [invocation invoke];
            payload[@"load_messages_selector"] = selectorName;
            return YES;
        } @catch (NSException *exc) {
            payload[@"load_messages_exception"] = Describe(exc);
        }
    }
    return NO;
}

static BOOL InvokeLoadMessagesAroundGUID(id chat, NSString *guid, NSInteger beforeCount, NSInteger afterCount, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"loadMessagesBeforeAndAfterGUID:numberOfMessagesToLoadBeforeGUID:numberOfMessagesToLoadAfterGUID:loadImmediately:threadIdentifier:");
    if (!chat || !sel || ![chat respondsToSelector:sel]) {
        return NO;
    }
    @try {
        NSMethodSignature *signature = [chat methodSignatureForSelector:sel];
        if (!signature) {
            return NO;
        }
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:chat];
        [invocation setSelector:sel];
        id guidArg = guid;
        NSInteger beforeArg = beforeCount;
        NSInteger afterArg = afterCount;
        BOOL loadImmediately = YES;
        id threadIdentifier = nil;
        [invocation setArgument:&guidArg atIndex:2];
        [invocation setArgument:&beforeArg atIndex:3];
        [invocation setArgument:&afterArg atIndex:4];
        [invocation setArgument:&loadImmediately atIndex:5];
        [invocation setArgument:&threadIdentifier atIndex:6];
        [invocation invoke];
        payload[@"load_messages_selector"] = @"loadMessagesBeforeAndAfterGUID:numberOfMessagesToLoadBeforeGUID:numberOfMessagesToLoadAfterGUID:loadImmediately:threadIdentifier:";
        return YES;
    } @catch (NSException *exc) {
        payload[@"load_messages_exception"] = Describe(exc);
        return NO;
    }
}

static NSString *StringProp(id target, NSString *name) {
    id value = Call0(target, name);
    if ([value isKindOfClass:[NSString class]]) {
        return value;
    }
    return Describe(value);
}

static NSNumber *NumberProp(id target, NSString *name) {
    id value = Call0(target, name);
    if ([value isKindOfClass:[NSNumber class]]) {
        return value;
    }
    return nil;
}

static NSMutableDictionary *DumpMessageLike(id message) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!message) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([message class]) ?: @"";
    payload[@"description"] = Describe(message);
    payload[@"guid"] = StringProp(message, @"guid") ?: @"";
    payload[@"text"] = StringProp(message, @"text") ?: @"";
    payload[@"body"] = StringProp(message, @"body") ?: @"";
    payload[@"subject"] = StringProp(message, @"subject") ?: @"";
    payload[@"sender"] = StringProp(message, @"sender") ?: @"";
    payload[@"threadIdentifier"] = StringProp(message, @"threadIdentifier") ?: @"";
    payload[@"threadOriginator"] = Describe(Call0(message, @"threadOriginator")) ?: @"";
    payload[@"associatedMessageGUID"] = StringProp(message, @"associatedMessageGUID") ?: @"";
    payload[@"associatedMessageRange"] = Describe(Call0(message, @"associatedMessageRange")) ?: @"";
    payload[@"associatedMessageType"] = Describe(Call0(message, @"associatedMessageType")) ?: @"";
    payload[@"associatedMessageEmoji"] = StringProp(message, @"associatedMessageEmoji") ?: @"";
    payload[@"messageSummaryInfo"] = Describe(Call0(message, @"messageSummaryInfo")) ?: @"";
    payload[@"replyCountsByPart"] = Describe(Call0(message, @"replyCountsByPart")) ?: @"";
    payload[@"partCount"] = Describe(Call0(message, @"partCount")) ?: @"";
    return payload;
}

static id BuildHandle(id account, NSString *identifier) {
    Class handleClass = NSClassFromString(@"IMHandle");
    if (!handleClass || !identifier.length) {
        return nil;
    }
    id handle = [handleClass alloc];
    SEL initSel = NSSelectorFromString(@"initWithAccount:ID:alreadyCanonical:");
    if (handle && initSel && [handle respondsToSelector:initSel]) {
        return ((id(*)(id, SEL, id, id, BOOL))objc_msgSend)(handle, initSel, account, identifier, YES);
    }
    return nil;
}

static id BuildReplyMessage(id account, NSString *text, NSString *parentGuid, NSString *threadIdentifier) {
    Class messageClass = NSClassFromString(@"IMMessage");
    if (!messageClass) {
        return nil;
    }
    NSString *sender = @"";
    id senderValue = Call0(account, @"login");
    if ([senderValue isKindOfClass:[NSString class]]) {
        sender = senderValue;
    } else {
        sender = Describe(senderValue);
    }

    SEL assocSel = NSSelectorFromString(@"instantMessageWithAssociatedMessageContent:associatedMessageGUID:associatedMessageType:associatedMessageRange:associatedMessageEmoji:messageSummaryInfo:threadIdentifier:");
    if ([messageClass respondsToSelector:assocSel]) {
        NSAttributedString *content = [[NSAttributedString alloc] initWithString:text ?: @""];
        NSRange range = NSMakeRange(0, 0);
        NSValue *rangeValue = [NSValue valueWithRange:range];
        return ((id(*)(id, SEL, id, id, long long, id, id, id, id))objc_msgSend)(
            messageClass,
            assocSel,
            content,
            parentGuid,
            (long long)0,
            rangeValue,
            nil,
            nil,
            threadIdentifier
        );
    }

    SEL fallbackSel = NSSelectorFromString(@"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:");
    if ([messageClass respondsToSelector:fallbackSel]) {
        NSAttributedString *content = [[NSAttributedString alloc] initWithString:text ?: @""];
        return ((id(*)(id, SEL, id, id, id, unsigned long long, id))objc_msgSend)(
            messageClass,
            fallbackSel,
            content,
            nil,
            @[],
            0ULL,
            threadIdentifier
        );
    }
    return nil;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int index = 1; index < argc; index += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[index]]];
        }

        NSString *chatGuid = ArgValue(args, @"--chat-guid", @"any;-;btuckercraig@gmail.com");
        NSString *identifier = ArgValue(args, @"--identifier", @"btuckercraig@gmail.com");
        NSString *messageGuid = ArgValue(args, @"--message-guid", @"");
        NSString *replyText = ArgValue(args, @"--text", @"");
        unsigned long long capabilities = ArgULL(args, @"--capabilities", 4485895ULL);
        BOOL send = HasFlag(args, @"--send");

        [NSApplication sharedApplication];
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);

        NSMutableDictionary *payload = [NSMutableDictionary dictionary];
        payload[@"chat_guid"] = chatGuid ?: @"";
        payload[@"identifier"] = identifier ?: @"";
        payload[@"message_guid"] = messageGuid ?: @"";
        payload[@"send"] = @(send);
        payload[@"requested_capabilities"] = @(capabilities);

        id daemonClass = NSClassFromString(@"IMDaemonController");
        id daemon = Call0(daemonClass, @"sharedController");
        if (!daemon) {
            daemon = Call0(daemonClass, @"sharedInstance");
        }
        payload[@"daemon"] = Describe(daemon);
        payload[@"daemon_process_context"] = Describe(Call0(daemon, @"processContext")) ?: @"";
        payload[@"daemon_process_capabilities_before"] = @(CallULL0(daemon, @"processCapabilities"));
        CallVoidULL1(daemon, @"setProcessCapabilities:", capabilities);
        payload[@"daemon_process_capabilities_after"] = @(CallULL0(daemon, @"processCapabilities"));
        payload[@"daemon_connect_result"] = @(InvokeDaemonConnect(daemon, capabilities, payload));
        CallVoid0(daemon, @"loadAllChats");
        for (NSInteger index = 0; index < 20; index += 1) {
            [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.15]];
        }

        id registryClass = NSClassFromString(@"IMChatRegistry");
        id registry = Call0(registryClass, @"sharedRegistry");
        payload[@"registry"] = Describe(registry);

        id chat = nil;
        NSArray<NSString *> *chatSelectors = @[
            @"existingChatWithGUID:",
            @"existingChatWithChatIdentifier:",
        ];
        for (NSString *selectorName in chatSelectors) {
            chat = SafeCall1(registry, selectorName, chatGuid, payload, selectorName);
            if (chat) {
                payload[@"chat_selector"] = selectorName;
                break;
            }
        }

        id accountController = Call0(NSClassFromString(@"IMAccountController"), @"sharedInstance");
        id activeAccount = Call0(accountController, @"activeIMessageAccount");
        if (!activeAccount) {
            activeAccount = Call0(chat, @"account");
        }
        payload[@"active_account"] = Describe(activeAccount);
        payload[@"active_account_login"] = StringProp(activeAccount, @"login") ?: @"";

        id handle = BuildHandle(activeAccount, identifier);
        payload[@"handle"] = Describe(handle);
        payload[@"handle_class"] = handle ? NSStringFromClass([handle class]) : @"";
        payload[@"handle_id"] = StringProp(handle, @"ID") ?: @"";

        if (!chat) {
            chat = SafeCall1(registry, @"existingChatWithHandle:", handle, payload, @"existingChatWithHandle");
            if (chat) {
                payload[@"chat_selector"] = @"existingChatWithHandle:";
            }
        }
        if (!chat) {
            chat = SafeCall1(registry, @"existingChatForIMHandle:", handle, payload, @"existingChatForIMHandle");
            if (chat) {
                payload[@"chat_selector"] = @"existingChatForIMHandle:";
            }
        }
        if (!chat) {
            chat = SafeCall1(registry, @"chatForIMHandle:", handle, payload, @"chatForIMHandle");
            if (chat) {
                payload[@"chat_selector"] = @"chatForIMHandle:";
            }
        }
        if (!chat) {
            chat = SafeCall1(registry, @"chatWithHandle:", handle, payload, @"chatWithHandle");
            if (chat) {
                payload[@"chat_selector"] = @"chatWithHandle:";
            }
        }
        payload[@"chat"] = Describe(chat);
        payload[@"chat_class"] = chat ? NSStringFromClass([chat class]) : @"";
        payload[@"chat_guid_runtime"] = StringProp(chat, @"guid") ?: @"";
        payload[@"chat_roomName"] = StringProp(chat, @"roomName") ?: @"";
        payload[@"chat_identifier"] = StringProp(chat, @"chatIdentifier") ?: @"";
        payload[@"chat_account"] = Describe(Call0(chat, @"account")) ?: @"";

        if (chat && messageGuid.length) {
            BOOL loaded = InvokeLoadMessagesUpToGUID(chat, messageGuid, 50, payload);
            if (!loaded) {
                loaded = InvokeLoadMessagesAroundGUID(chat, messageGuid, 10, 10, payload);
            }
            payload[@"load_messages_invoked"] = @(loaded);
            for (NSInteger index = 0; index < 20; index += 1) {
                [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.15]];
            }
        }

        id parent = nil;
        if (chat && messageGuid.length) {
            for (NSInteger index = 0; index < 500 && !parent; index += 1) {
                parent = SafeCall1(chat, @"messageForGUID:", messageGuid, payload, @"messageForGUID");
                if (!parent) {
                    parent = SafeCall1(chat, @"messageItemForGUID:", messageGuid, payload, @"messageItemForGUID");
                }
                if (!parent) {
                    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.02]];
                }
            }
        }
        payload[@"parent"] = DumpMessageLike(parent);

        NSString *threadIdentifier = StringProp(parent, @"threadIdentifier");
        if (!threadIdentifier.length) {
            threadIdentifier = messageGuid;
        }
        payload[@"derived_thread_identifier"] = threadIdentifier ?: @"";

        if (send && chat && messageGuid.length && replyText.length) {
            id message = BuildReplyMessage(activeAccount ?: Call0(chat, @"account"), replyText, messageGuid, threadIdentifier);
            payload[@"outgoing"] = DumpMessageLike(message);

            @try {
                BOOL invoked = NO;
                SEL sendWithAccountSel = NSSelectorFromString(@"sendMessage:withAccount:");
                if (sendWithAccountSel && [chat respondsToSelector:sendWithAccountSel] && activeAccount) {
                    ((void(*)(id, SEL, id, id))objc_msgSend)(chat, sendWithAccountSel, message, activeAccount);
                    payload[@"send_selector"] = @"sendMessage:withAccount:";
                    invoked = YES;
                } else {
                    SEL sendSel = NSSelectorFromString(@"sendMessage:");
                    if (sendSel && [chat respondsToSelector:sendSel]) {
                        ((void(*)(id, SEL, id))objc_msgSend)(chat, sendSel, message);
                        payload[@"send_selector"] = @"sendMessage:";
                        invoked = YES;
                    }
                }
                payload[@"send_invoked"] = @(invoked);
            } @catch (NSException *exc) {
                payload[@"send_exception"] = Describe(exc);
            }

            for (NSInteger index = 0; index < 40; index += 1) {
                [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.15]];
            }
        }

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
