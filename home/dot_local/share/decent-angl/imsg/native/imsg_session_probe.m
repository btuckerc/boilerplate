#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>

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

static NSInteger ArgInt(NSArray<NSString *> *args, NSString *flag, NSInteger fallback) {
    NSString *value = ArgValue(args, flag, nil);
    if (!value.length) {
        return fallback;
    }
    return (NSInteger)[value integerValue];
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

static BOOL CallBool0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return NO;
    }
    return ((BOOL(*)(id, SEL))objc_msgSend)(target, sel);
}

static void SetObjectProperty(id target, NSString *selectorName, id value) {
    SEL sel = NSSelectorFromString(selectorName);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, id))objc_msgSend)(target, sel, value);
}

static NSString *StringProp(id target, NSString *name) {
    id value = Call0(target, name);
    if ([value isKindOfClass:[NSString class]]) {
        return value;
    }
    return Describe(value);
}

static NSDictionary *DumpItem(id item) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!item) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([item class]) ?: @"";
    payload[@"description"] = Describe(item);
    payload[@"guid"] = StringProp(item, @"guid") ?: @"";
    payload[@"sender"] = StringProp(item, @"sender") ?: @"";
    payload[@"account"] = StringProp(item, @"account") ?: @"";
    payload[@"accountID"] = StringProp(item, @"accountID") ?: @"";
    payload[@"service"] = StringProp(item, @"service") ?: @"";
    payload[@"handle"] = StringProp(item, @"handle") ?: @"";
    payload[@"roomName"] = StringProp(item, @"roomName") ?: @"";
    payload[@"replyToGUID"] = StringProp(item, @"replyToGUID") ?: @"";
    payload[@"threadIdentifier"] = StringProp(item, @"threadIdentifier") ?: @"";
    payload[@"plainBody"] = StringProp(item, @"plainBody") ?: @"";
    payload[@"body"] = Describe(Call0(item, @"body")) ?: @"";
    payload[@"messageSummaryInfo"] = Describe(Call0(item, @"messageSummaryInfo")) ?: @"";
    payload[@"groupActivity"] = Describe(Call0(item, @"groupActivity")) ?: @"";
    payload[@"partCount"] = Describe(Call0(item, @"partCount")) ?: @"";
    payload[@"isReply"] = @(CallBool0(item, @"isReply"));
    id threadOriginator = Call0(item, @"threadOriginator");
    payload[@"threadOriginator"] = Describe(threadOriginator);
    payload[@"threadOriginatorGUID"] = StringProp(threadOriginator, @"guid") ?: @"";
    payload[@"threadOriginatorSummary"] = Describe(Call0(threadOriginator, @"messageSummaryInfo")) ?: @"";
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
    payload[@"serviceName"] = StringProp(chat, @"serviceName") ?: @"";
    payload[@"accountID"] = StringProp(chat, @"accountID") ?: @"";
    payload[@"displayName"] = StringProp(chat, @"displayName") ?: @"";
    payload[@"lastAddressedLocalHandle"] = StringProp(chat, @"lastAddressedLocalHandle") ?: @"";
    payload[@"style"] = Describe(Call0(chat, @"style")) ?: @"";
    payload[@"account"] = Describe(Call0(chat, @"account")) ?: @"";
    payload[@"serviceSession"] = Describe(Call0(chat, @"serviceSession")) ?: @"";
    payload[@"lastMessage"] = Describe(Call0(chat, @"lastMessage")) ?: @"";
    return payload;
}

static NSDictionary *DumpSession(id session) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!session) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([session class]) ?: @"";
    payload[@"description"] = Describe(session);
    payload[@"account"] = Describe(Call0(session, @"account")) ?: @"";
    payload[@"accounts"] = Describe(Call0(session, @"accounts")) ?: @"";
    payload[@"service"] = Describe(Call0(session, @"service")) ?: @"";
    payload[@"loginID"] = StringProp(session, @"loginID") ?: @"";
    payload[@"callerURI"] = StringProp(session, @"callerURI") ?: @"";
    payload[@"registeredURIs"] = Describe(Call0(session, @"registeredURIs")) ?: @"";
    payload[@"registrationStatus"] = Describe(Call0(session, @"registrationStatus")) ?: @"";
    payload[@"registrationError"] = Describe(Call0(session, @"registrationError")) ?: @"";
    payload[@"isActive"] = @(CallBool0(session, @"isActive"));
    payload[@"idsAccount"] = Describe(Call0(session, @"idsAccount")) ?: @"";
    return payload;
}

static NSDictionary *DumpAccount(id account) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!account) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([account class]) ?: @"";
    payload[@"description"] = Describe(account);
    return payload;
}

static id CreateService(void) {
    Class serviceClass = NSClassFromString(@"IMDService");
    if (!serviceClass) {
        return nil;
    }
    NSBundle *bundle = [NSBundle bundleWithPath:@"/System/Library/Messages/PlugIns/iMessage.imservice"];
    if (!bundle) {
        return nil;
    }
    id service = ((id(*)(id, SEL, id))objc_msgSend)([serviceClass alloc], NSSelectorFromString(@"initWithBundle:"), bundle);
    CallVoid0(service, @"loadServiceBundle");
    return service;
}

static id CreateAccount(id service, NSString *accountID, NSString *loginID) {
    if (!service || !accountID.length) {
        return nil;
    }
    id defaults = Call0(service, @"defaultAccountSettings");
    id account = nil;
    SEL newAccountSel = NSSelectorFromString(@"newAccountWithAccountDefaults:accountID:");
    if (newAccountSel && [service respondsToSelector:newAccountSel]) {
        account = ((id(*)(id, SEL, id, id))objc_msgSend)(service, newAccountSel, defaults ?: @{}, accountID);
    }
    if (!account) {
        Class accountClass = NSClassFromString(@"IMDAccount");
        SEL initSel = NSSelectorFromString(@"initWithAccountID:defaults:service:");
        if (accountClass && initSel) {
            account = ((id(*)(id, SEL, id, id, id))objc_msgSend)([accountClass alloc], initSel, accountID, defaults ?: @{}, service);
        }
    }
    if (account && loginID.length) {
        SetObjectProperty(account, @"setLoginID:", loginID);
    }
    CallVoid0(account, @"createSessionIfNecessary");
    return account;
}

static id InvokeChatLookup(id session, NSString *chatIdentifier, NSInteger style, id account, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"chatForChatIdentifier:style:account:updatingAccount:");
    if (!session || !chatIdentifier.length || !sel || ![session respondsToSelector:sel]) {
        return nil;
    }
    @try {
        NSMethodSignature *signature = [session methodSignatureForSelector:sel];
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:session];
        [invocation setSelector:sel];
        id chatArg = chatIdentifier;
        BOOL updatingAccount = NO;
        [invocation setArgument:&chatArg atIndex:2];
        const char *styleType = [signature getArgumentTypeAtIndex:3];
        if (styleType && styleType[0] == 'q') {
            long long styleArg = (long long)style;
            [invocation setArgument:&styleArg atIndex:3];
        } else {
            int styleArg = (int)style;
            [invocation setArgument:&styleArg atIndex:3];
        }
        [invocation setArgument:&account atIndex:4];
        [invocation setArgument:&updatingAccount atIndex:5];
        [invocation invoke];
        __unsafe_unretained id chat = nil;
        [invocation getReturnValue:&chat];
        payload[@"chat_lookup_by_identifier"] = DumpChat(chat);
        return chat;
    } @catch (NSException *exc) {
        payload[@"chat_lookup_exception"] = Describe(exc);
        return nil;
    }
}

static void InvokeConfigureAccountInformation(id session, id item, id account, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"_configureAccountInformationOnItem:withAccount:");
    if (!session || !item || !account || !sel || ![session respondsToSelector:sel]) {
        return;
    }
    @try {
        ((void(*)(id, SEL, id, id))objc_msgSend)(session, sel, item, account);
    } @catch (NSException *exc) {
        payload[@"configure_account_exception"] = Describe(exc);
    }
}

static void InvokeConfigureIdentifier(id session, id item, NSString *identifier, NSInteger style, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"_configureIdentifierForOutgoingItem:withIdentifier:withStyle:");
    if (!session || !item || !identifier.length || !sel || ![session respondsToSelector:sel]) {
        return;
    }
    @try {
        NSMethodSignature *signature = [session methodSignatureForSelector:sel];
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:session];
        [invocation setSelector:sel];
        [invocation setArgument:&item atIndex:2];
        id identifierArg = identifier;
        [invocation setArgument:&identifierArg atIndex:3];
        const char *styleType = [signature getArgumentTypeAtIndex:4];
        if (styleType && styleType[0] == 'q') {
            long long styleArg = (long long)style;
            [invocation setArgument:&styleArg atIndex:4];
        } else {
            int styleArg = (int)style;
            [invocation setArgument:&styleArg atIndex:4];
        }
        [invocation invoke];
    } @catch (NSException *exc) {
        payload[@"configure_identifier_exception"] = Describe(exc);
    }
}

static void InvokeConfigureSessionInformation(id session, id item, id chat, NSInteger style, id account, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"_configureSessionInformationOnItem:toChat:withStyle:forAccount:");
    if (!session || !item || !chat || !sel || ![session respondsToSelector:sel]) {
        return;
    }
    @try {
        NSMethodSignature *signature = [session methodSignatureForSelector:sel];
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:session];
        [invocation setSelector:sel];
        [invocation setArgument:&item atIndex:2];
        [invocation setArgument:&chat atIndex:3];
        const char *styleType = [signature getArgumentTypeAtIndex:4];
        if (styleType && styleType[0] == 'q') {
            long long styleArg = (long long)style;
            [invocation setArgument:&styleArg atIndex:4];
        } else {
            int styleArg = (int)style;
            [invocation setArgument:&styleArg atIndex:4];
        }
        [invocation setArgument:&account atIndex:5];
        [invocation invoke];
    } @catch (NSException *exc) {
        payload[@"configure_session_exception"] = Describe(exc);
    }
}

static void InvokeSetReply(id session, id item, id chat, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"_setReplyGUIDOnMessage:forChat:");
    if (!session || !item || !chat || !sel || ![session respondsToSelector:sel]) {
        return;
    }
    @try {
        ((void(*)(id, SEL, id, id))objc_msgSend)(session, sel, item, chat);
    } @catch (NSException *exc) {
        payload[@"set_reply_exception"] = Describe(exc);
    }
}

static void InvokeSend(id session, id item, id chat, NSInteger style, id account, NSString *method, NSMutableDictionary *payload) {
    NSString *selectorName = [method isEqualToString:@"process"]
        ? @"processMessageForSending:toChat:style:allowWatchdog:account:completionBlock:"
        : @"sendMessage:toChat:style:account:";
    SEL sel = NSSelectorFromString(selectorName);
    if (!session || !item || !chat || !sel || ![session respondsToSelector:sel]) {
        payload[@"send_error"] = @"missing send selector";
        payload[@"send_selector"] = selectorName;
        return;
    }
    payload[@"send_selector"] = selectorName;
    @try {
        NSMethodSignature *signature = [session methodSignatureForSelector:sel];
        NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
        [invocation setTarget:session];
        [invocation setSelector:sel];
        [invocation setArgument:&item atIndex:2];
        [invocation setArgument:&chat atIndex:3];
        const char *styleType = [signature getArgumentTypeAtIndex:4];
        if (styleType && styleType[0] == 'q') {
            long long styleArg = (long long)style;
            [invocation setArgument:&styleArg atIndex:4];
        } else {
            int styleArg = (int)style;
            [invocation setArgument:&styleArg atIndex:4];
        }
        if ([method isEqualToString:@"process"]) {
            BOOL allowWatchdog = YES;
            id block = nil;
            [invocation setArgument:&allowWatchdog atIndex:5];
            [invocation setArgument:&account atIndex:6];
            [invocation setArgument:&block atIndex:7];
        } else {
            [invocation setArgument:&account atIndex:5];
        }
        [invocation invoke];
        payload[@"send_invoked"] = @YES;
    } @catch (NSException *exc) {
        payload[@"send_exception"] = Describe(exc);
    }
}

static id BuildOutgoingReply(id parentItem, NSString *text, NSMutableDictionary *payload) {
    id item = Call0(parentItem, @"copyAsReplied");
    if (item) {
        payload[@"builder"] = @"copyAsReplied";
    }
    if (!item) {
        Class itemClass = NSClassFromString(@"IMMessageItem");
        SEL initSel = NSSelectorFromString(@"initWithSender:time:body:attributes:fileTransferGUIDs:flags:error:guid:threadIdentifier:");
        if (itemClass && initSel) {
            NSString *threadIdentifier = StringProp(parentItem, @"threadIdentifier");
            if (!threadIdentifier.length) {
                id root = Call0(parentItem, @"threadOriginator");
                threadIdentifier = StringProp(root, @"guid");
            }
            item = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id))objc_msgSend)(
                [itemClass alloc],
                initSel,
                StringProp(parentItem, @"account") ?: @"",
                [NSDate date],
                [[NSAttributedString alloc] initWithString:text ?: @""],
                @{},
                @[],
                0ULL,
                nil,
                [[NSUUID UUID] UUIDString],
                threadIdentifier ?: @""
            );
            payload[@"builder"] = @"initWithSender:time:body:attributes:fileTransferGUIDs:flags:error:guid:threadIdentifier:";
        }
    }
    if (!item) {
        return nil;
    }
    NSString *guid = [[NSUUID UUID] UUIDString];
    SetObjectProperty(item, @"setGuid:", guid);
    SetObjectProperty(item, @"setBody:", [[NSAttributedString alloc] initWithString:text ?: @""]);
    SetObjectProperty(item, @"setPlainBody:", text ?: @"");
    SetObjectProperty(item, @"setFileTransferGUIDs:", @[]);
    payload[@"outgoing_guid"] = guid;
    return item;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int index = 1; index < argc; index += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[index]]];
        }

        NSString *accountID = ArgValue(args, @"--account-id", @"5B2B8F92-C4E0-4A65-87FF-32D3671BD5F8");
        NSString *loginID = ArgValue(args, @"--login-id", @"E:btuckerc.dev@gmail.com");
        NSString *chatGuid = ArgValue(args, @"--chat-guid", @"");
        NSString *messageGuid = ArgValue(args, @"--message-guid", @"");
        NSString *identifier = ArgValue(args, @"--identifier", @"btuckercraig@gmail.com");
        NSString *text = ArgValue(args, @"--text", @"");
        NSString *sendMethod = ArgValue(args, @"--method", @"process");
        NSInteger style = ArgInt(args, @"--style", 45);
        BOOL send = HasFlag(args, @"--send");
        BOOL skipLogin = HasFlag(args, @"--skip-login");
        BOOL existingOnly = HasFlag(args, @"--existing-only");

        fprintf(stderr, "probe:start\n");
        fflush(stderr);
        [NSApplication sharedApplication];
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);
        fprintf(stderr, "probe:frameworks\n");
        fflush(stderr);

        NSMutableDictionary *payload = [NSMutableDictionary dictionary];
        payload[@"account_id"] = accountID ?: @"";
        payload[@"login_id"] = loginID ?: @"";
        payload[@"chat_guid"] = chatGuid ?: @"";
        payload[@"message_guid"] = messageGuid ?: @"";
        payload[@"identifier"] = identifier ?: @"";
        payload[@"text"] = text ?: @"";
        payload[@"send"] = @(send);
        payload[@"method"] = sendMethod ?: @"";

        id service = CreateService();
        fprintf(stderr, "probe:service=%s\n", [Describe(service) UTF8String]);
        fflush(stderr);
        payload[@"service"] = Describe(service);
        payload[@"service_internal_name"] = StringProp(service, @"internalName") ?: @"";
        payload[@"service_session_class"] = Describe(Call0(service, @"sessionClass")) ?: @"";
        payload[@"service_default_account_settings"] = Describe(Call0(service, @"defaultAccountSettings")) ?: @"";

        id sessionClass = NSClassFromString(@"IMDServiceSession");
        id session = Call1(sessionClass, @"existingServiceSessionForService:", service);
        payload[@"session_existing"] = DumpSession(session);
        fprintf(stderr, "probe:existing-session=%s\n", [Describe(session) UTF8String]);
        fflush(stderr);

        id account = nil;
        if (!existingOnly) {
            account = CreateAccount(service, accountID, loginID);
            fprintf(stderr, "probe:account=%s\n", [Describe(account) UTF8String]);
            fflush(stderr);
            payload[@"account_before_login"] = @{
                @"description": Describe(account),
            };

            if (!session) {
                fprintf(stderr, "probe:session-from-account-begin\n");
                fflush(stderr);
                session = Call0(account, @"session");
                fprintf(stderr, "probe:session-from-account=%s\n", [Describe(session) UTF8String]);
                fflush(stderr);
            }
            if (!session) {
                Class appleSessionClass = NSClassFromString(@"IMDAppleServiceSession");
                SEL initSel = NSSelectorFromString(@"initWithAccount:service:");
                if (appleSessionClass && initSel) {
                    session = ((id(*)(id, SEL, id, id))objc_msgSend)([appleSessionClass alloc], initSel, account, service);
                    SetObjectProperty(account, @"setSession:", session);
                }
            }
        }
        payload[@"session_initial"] = DumpSession(session);
        fprintf(stderr, "probe:session-initial=%s\n", [Describe(session) UTF8String]);
        fflush(stderr);

        if (!skipLogin && account && session) {
            fprintf(stderr, "probe:login-begin\n");
            fflush(stderr);
            CallVoid1(session, @"addAccount:", account);
            fprintf(stderr, "probe:login-addAccount\n");
            fflush(stderr);
            CallVoid1(session, @"loginServiceSessionWithAccount:", account);
            fprintf(stderr, "probe:login-service-session\n");
            fflush(stderr);
            CallVoid1(session, @"loginWithAccount:", account);
            fprintf(stderr, "probe:login-with-account\n");
            fflush(stderr);
            CallVoid1(session, @"registerAccount:", account);
            fprintf(stderr, "probe:login-register\n");
            fflush(stderr);
            CallVoid0(session, @"refreshRegistration");
            fprintf(stderr, "probe:login-refresh\n");
            fflush(stderr);
            CallVoid0(session, @"reIdentify");
            fprintf(stderr, "probe:login-reidentify\n");
            fflush(stderr);
        }

        for (NSInteger index = 0; index < 30; index += 1) {
            [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.2]];
        }
        fprintf(stderr, "probe:post-login-loop\n");
        fflush(stderr);

        payload[@"account_after_login"] = account ? @{@"description": Describe(account)} : @{};
        payload[@"session_after_login"] = DumpSession(session);

        id item = messageGuid.length ? Call1(session, @"itemWithGUID:", messageGuid) : nil;
        fprintf(stderr, "probe:item=%s\n", [Describe(item) UTF8String]);
        fflush(stderr);
        payload[@"item_lookup"] = DumpItem(item);

        id rootItem = Call0(item, @"threadOriginator");
        if (!rootItem && item) {
            rootItem = item;
        }
        payload[@"root_item"] = DumpItem(rootItem);

        id chat = messageGuid.length ? Call1(session, @"chatForItemWithGUID:", messageGuid) : nil;
        payload[@"chat_from_item"] = DumpChat(chat);
        fprintf(stderr, "probe:chat=%s\n", [Describe(chat) UTF8String]);
        fflush(stderr);

        if (!chat && chatGuid.length) {
            chat = InvokeChatLookup(session, chatGuid, style, account, payload);
        }

        if (send && item && text.length) {
            id outgoing = BuildOutgoingReply(item, text, payload);
            payload[@"outgoing_before_config"] = DumpItem(outgoing);
            fprintf(stderr, "probe:outgoing-before=%s\n", [Describe(outgoing) UTF8String]);
            fflush(stderr);

            SetObjectProperty(outgoing, @"setReplyToGUID:", messageGuid);
            if (rootItem && outgoing != rootItem) {
                SetObjectProperty(outgoing, @"setThreadOriginator:", rootItem);
                NSString *rootGuid = StringProp(rootItem, @"guid");
                if (rootGuid.length) {
                    SetObjectProperty(outgoing, @"setThreadIdentifier:", rootGuid);
                }
            }

            InvokeConfigureAccountInformation(session, outgoing, account, payload);
            InvokeConfigureIdentifier(session, outgoing, identifier, style, payload);
            InvokeConfigureSessionInformation(session, outgoing, chat, style, account, payload);
            CallVoid1(session, @"_configureTimeOnOutgoingItem:", outgoing);
            InvokeSetReply(session, outgoing, chat, payload);

            payload[@"outgoing_after_config"] = DumpItem(outgoing);
            fprintf(stderr, "probe:outgoing-after=%s\n", [Describe(outgoing) UTF8String]);
            fflush(stderr);
            InvokeSend(session, outgoing, chat, style, account, sendMethod, payload);
            fprintf(stderr, "probe:send-invoked\n");
            fflush(stderr);

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
