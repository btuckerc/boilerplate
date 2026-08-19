#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>
#import <objc/runtime.h>

static void SetObjectProperty(id target, NSString *selectorName, id value);
static void SetBoolProperty(id target, NSString *selectorName, BOOL value);

static id Call0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return nil;
    }
    return ((id(*)(id, SEL))objc_msgSend)(target, sel);
}

static void CallVoid0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL))objc_msgSend)(target, sel);
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

static NSString *StringProp(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return @"";
    }
    id value = ((id(*)(id, SEL))objc_msgSend)(target, sel);
    return [value isKindOfClass:[NSString class]] ? value : Describe(value);
}

static NSString *ArgValue(NSArray<NSString *> *args, NSString *flag, NSString *fallback) {
    NSUInteger index = [args indexOfObject:flag];
    if (index == NSNotFound || index + 1 >= [args count]) {
        return fallback;
    }
    return args[index + 1];
}

static NSInteger ArgInt(NSArray<NSString *> *args, NSString *flag, NSInteger fallback) {
    NSString *value = ArgValue(args, flag, nil);
    if (!value || [value length] == 0) {
        return fallback;
    }
    return (NSInteger)[value integerValue];
}

static id BuildIMMessage(NSString *sender, NSString *text, NSString *threadIdentifier, NSMutableDictionary *debug) {
    Class messageClass = NSClassFromString(@"IMMessage");
    if (!messageClass) {
        debug[@"build_error"] = @"IMMessage class missing";
        return nil;
    }
    SEL simpleSel = NSSelectorFromString(@"instantMessageWithText:flags:threadIdentifier:");
    if ([messageClass respondsToSelector:simpleSel]) {
        unsigned long long flags = 0;
        NSAttributedString *attributedText = [[NSAttributedString alloc] initWithString:text ?: @""];
        id result = ((id(*)(id, SEL, id, unsigned long long, id))objc_msgSend)(
            messageClass,
            simpleSel,
            attributedText,
            flags,
            [threadIdentifier length] ? threadIdentifier : nil
        );
        debug[@"message_desc"] = Describe(result);
        debug[@"message_factory"] = @"instantMessageWithText:flags:threadIdentifier:";
        return result;
    }

    SEL richSel = NSSelectorFromString(@"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:");
    if ([messageClass respondsToSelector:richSel]) {
        unsigned long long flags = 0;
        NSAttributedString *attributedText = [[NSAttributedString alloc] initWithString:text ?: @""];
        id result = ((id(*)(id, SEL, id, id, id, unsigned long long, id))objc_msgSend)(
            messageClass,
            richSel,
            attributedText,
            nil,
            @[],
            flags,
            [threadIdentifier length] ? threadIdentifier : nil
        );
        debug[@"message_desc"] = Describe(result);
        debug[@"message_factory"] = @"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:";
        return result;
    }

    debug[@"build_error"] = @"no IMMessage factory selector found";
    return nil;
}

static id BuildMessageItem(
    NSString *sender,
    NSString *identifier,
    NSString *accountID,
    NSString *service,
    NSString *text,
    NSString *threadIdentifier,
    NSString *replyGuid,
    NSMutableDictionary *debug
) {
    Class itemClass = NSClassFromString(@"IMMessageItem");
    if (!itemClass) {
        debug[@"build_error"] = @"IMMessageItem class missing";
        return nil;
    }

    SEL initSel = NSSelectorFromString(@"initWithSender:time:body:attributes:fileTransferGUIDs:flags:error:guid:threadIdentifier:");
    if (![itemClass instancesRespondToSelector:initSel]) {
        debug[@"build_error"] = @"IMMessageItem init selector missing";
        return nil;
    }

    id instance = [itemClass alloc];
    NSDate *time = [NSDate date];
    NSAttributedString *body = [[NSAttributedString alloc] initWithString:text ?: @""];
    NSDictionary *attributes = @{};
    NSArray *fileTransferGUIDs = @[];
    unsigned long long flags = 0x100005ULL;
    id error = nil;
    NSString *guid = [[NSUUID UUID] UUIDString];

    id item = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id))objc_msgSend)(
        instance,
        initSel,
        sender ?: identifier ?: @"",
        time,
        body,
        attributes,
        fileTransferGUIDs,
        flags,
        error,
        guid,
        threadIdentifier ?: @""
    );

    SetObjectProperty(item, @"setAccountID:", accountID);
    SetObjectProperty(item, @"setAccount:", accountID);
    SetObjectProperty(item, @"setService:", service);
    SetObjectProperty(item, @"setHandle:", identifier);
    SetObjectProperty(item, @"setSender:", sender ?: identifier);
    SetObjectProperty(item, @"setReplyToGUID:", replyGuid);

    debug[@"message_guid"] = guid;
    debug[@"message_factory"] = @"IMMessageItem";
    debug[@"message_desc"] = Describe(item);
    return item;
}

static void SetObjectProperty(id target, NSString *selectorName, id value) {
    SEL sel = NSSelectorFromString(selectorName);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, id))objc_msgSend)(target, sel, value);
}

static void SetBoolProperty(id target, NSString *selectorName, BOOL value) {
    SEL sel = NSSelectorFromString(selectorName);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, BOOL))objc_msgSend)(target, sel, value);
}

static id BuildSimulatedMessage(
    NSString *chatGuid,
    NSString *identifier,
    NSString *sender,
    NSString *text,
    NSString *threadIdentifier,
    NSMutableDictionary *debug
) {
    Class simulatedClass = NSClassFromString(@"IMSPISimulatedMessage");
    if (!simulatedClass) {
        debug[@"build_error"] = @"IMSPISimulatedMessage class missing";
        return nil;
    }

    id message = [simulatedClass new];
    NSString *guid = [[NSUUID UUID] UUIDString];
    SetObjectProperty(message, @"setGuid:", guid);
    SetObjectProperty(message, @"setText:", text);
    SetObjectProperty(message, @"setServiceName:", @"iMessage");
    SetObjectProperty(message, @"setAccountID:", [sender length] ? sender : nil);
    SetBoolProperty(message, @"setFromMe:", YES);
    SetObjectProperty(message, @"setDate:", [NSDate date]);
    SetObjectProperty(message, @"setChatGUID:", [chatGuid length] ? chatGuid : nil);
    if ([identifier length]) {
        SetObjectProperty(message, @"setHandles:", @[identifier]);
        SetObjectProperty(message, @"setLastAddressedHandle:", identifier);
        SetObjectProperty(message, @"setSender:", identifier);
    }
    if ([threadIdentifier length]) {
        SetObjectProperty(message, @"setThreadIdentifier:", threadIdentifier);
    }
    debug[@"message_guid"] = guid;
    debug[@"message_desc"] = Describe(message);
    return message;
}

static id BuildAssociatedMessageItem(
    NSString *sender,
    NSString *identifier,
    NSString *accountID,
    NSString *service,
    NSString *text,
    NSString *parentGuid,
    NSString *threadIdentifier,
    NSString *replyGuid,
    NSMutableDictionary *debug
) {
    Class itemClass = NSClassFromString(@"IMAssociatedMessageItem");
    if (!itemClass) {
        debug[@"build_error"] = @"IMAssociatedMessageItem class missing";
        return nil;
    }

    SEL initSel = NSSelectorFromString(@"initWithSender:time:body:attributes:fileTransferGUIDs:flags:error:guid:associatedMessageGUID:associatedMessageType:associatedMessageRange:messageSummaryInfo:threadIdentifier:");
    if (![itemClass instancesRespondToSelector:initSel]) {
        debug[@"build_error"] = @"IMAssociatedMessageItem init selector missing";
        return nil;
    }

    id instance = [itemClass alloc];
    NSDate *time = [NSDate date];
    NSAttributedString *body = [[NSAttributedString alloc] initWithString:text ?: @""];
    NSDictionary *attributes = @{};
    NSArray *fileTransferGUIDs = @[];
    unsigned long long flags = 0;
    id error = nil;
    NSString *guid = [[NSUUID UUID] UUIDString];
    long long associatedType = 0;
    NSValue *associatedRange = [NSValue valueWithRange:NSMakeRange(0, 0)];
    id summaryInfo = nil;

    id item = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id, long long, id, id, id))objc_msgSend)(
        instance,
        initSel,
        sender ?: @"",
        time,
        body,
        attributes,
        fileTransferGUIDs,
        flags,
        error,
        guid,
        parentGuid ?: @"",
        associatedType,
        associatedRange,
        summaryInfo,
        threadIdentifier ?: @""
    );
    SetObjectProperty(item, @"setAccountID:", accountID);
    SetObjectProperty(item, @"setAccount:", accountID);
    SetObjectProperty(item, @"setService:", service);
    SetObjectProperty(item, @"setHandle:", identifier);
    SetObjectProperty(item, @"setSender:", sender ?: identifier);
    SetObjectProperty(item, @"setReplyToGUID:", replyGuid ?: parentGuid);
    debug[@"message_guid"] = guid;
    debug[@"message_factory"] = @"IMAssociatedMessageItem";
    debug[@"message_desc"] = Describe(item);
    return item;
}

static id PayloadForShape(id object, NSString *shape, NSMutableDictionary *debug) {
    if (!object) {
        return nil;
    }

    if (!shape.length || [shape isEqualToString:@"object"]) {
        return object;
    }

    if ([shape isEqualToString:@"dict"]) {
        if ([object respondsToSelector:NSSelectorFromString(@"copyDictionaryRepresentation")]) {
            id value = ((id(*)(id, SEL))objc_msgSend)(object, NSSelectorFromString(@"copyDictionaryRepresentation"));
            debug[@"payload_shape_applied"] = @"copyDictionaryRepresentation";
            debug[@"payload_desc"] = Describe(value);
            return value;
        }
        if ([object respondsToSelector:NSSelectorFromString(@"dictionaryRepresentation")]) {
            id value = ((id(*)(id, SEL))objc_msgSend)(object, NSSelectorFromString(@"dictionaryRepresentation"));
            debug[@"payload_shape_applied"] = @"dictionaryRepresentation";
            debug[@"payload_desc"] = Describe(value);
            return value;
        }
        debug[@"payload_shape_error"] = @"dictionaryRepresentation missing";
        return object;
    }

    if ([shape isEqualToString:@"remote"]) {
        SEL encodeSel = NSSelectorFromString(@"encodeWithIMRemoteObjectSerializedDictionary:");
        if (![object respondsToSelector:encodeSel]) {
            debug[@"payload_shape_error"] = @"encodeWithIMRemoteObjectSerializedDictionary missing";
            return object;
        }
        NSMutableDictionary *payload = [NSMutableDictionary dictionary];
        ((void(*)(id, SEL, id))objc_msgSend)(object, encodeSel, payload);
        debug[@"payload_shape_applied"] = @"encodeWithIMRemoteObjectSerializedDictionary";
        debug[@"payload_desc"] = Describe(payload);
        return payload;
    }

    debug[@"payload_shape_error"] = [NSString stringWithFormat:@"unknown payload shape %@", shape];
    return object;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        fprintf(stderr, "probe:start\n");
        fflush(stderr);
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *text = ArgValue(args, @"--text", @"probe");
        NSString *chatGuid = ArgValue(args, @"--chat-guid", @"");
        NSString *identifier = ArgValue(args, @"--identifier", @"");
        NSString *sender = ArgValue(args, @"--sender", @"E:btuckerc.dev@gmail.com");
        NSString *accountID = ArgValue(args, @"--account-id", @"");
        NSString *service = ArgValue(args, @"--service", @"iMessage");
        NSString *threadIdentifier = ArgValue(args, @"--thread-id", @"");
        NSString *parentGuid = ArgValue(args, @"--parent-guid", @"");
        NSString *replyGuid = ArgValue(args, @"--reply-guid", @"");
        NSString *carrier = ArgValue(args, @"--carrier", @"simulated");
        NSString *payloadShape = ArgValue(args, @"--payload-shape", @"object");
        NSInteger styleValue = ArgInt(args, @"--style", 45);

        NSMutableDictionary *debug = [NSMutableDictionary dictionary];
        debug[@"text"] = text ?: @"";
        debug[@"chat_guid"] = chatGuid ?: @"";
        debug[@"identifier"] = identifier ?: @"";
        debug[@"sender"] = sender ?: @"";
        debug[@"account_id"] = accountID ?: @"";
        debug[@"service"] = service ?: @"";
        debug[@"thread_identifier"] = threadIdentifier ?: @"";
        debug[@"parent_guid"] = parentGuid ?: @"";
        debug[@"reply_guid"] = replyGuid ?: @"";
        debug[@"carrier"] = carrier ?: @"";
        debug[@"payload_shape"] = payloadShape ?: @"";
        debug[@"style"] = @(styleValue);

        [NSApplication sharedApplication];
        fprintf(stderr, "probe:nsapp\n");
        fflush(stderr);
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);
        fprintf(stderr, "probe:dlopen\n");
        fflush(stderr);

        Class daemonClass = NSClassFromString(@"IMDaemonController");
        id daemon = Call0(daemonClass, @"sharedInstance");
        debug[@"daemon"] = Describe(daemon);
        fprintf(stderr, "probe:daemon=%s\n", [Describe(daemon) UTF8String]);
        fflush(stderr);
        CallVoid0(daemon, @"blockUntilConnected");
        fprintf(stderr, "probe:connected\n");
        fflush(stderr);
        CallVoid0(daemon, @"loadAllChats");
        fprintf(stderr, "probe:loadAllChats\n");
        fflush(stderr);
        for (NSInteger i = 0; i < 20; i += 1) {
            [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.15]];
        }
        fprintf(stderr, "probe:runloop-ready\n");
        fflush(stderr);

        id proxy = Call0(daemon, @"synchronousReplyingRemoteDaemon");
        debug[@"proxy"] = Describe(proxy);
        fprintf(stderr, "probe:proxy=%s\n", [Describe(proxy) UTF8String]);
        fflush(stderr);

        SEL sendSel = NSSelectorFromString(@"sendMessage:toChatID:identifier:style:account:");
        NSMethodSignature *signature = [proxy methodSignatureForSelector:sendSel];
        debug[@"signature"] = signature ? [signature debugDescription] : @"";
        if (signature) {
            NSMutableArray<NSString *> *argTypes = [NSMutableArray array];
            for (NSUInteger index = 0; index < [signature numberOfArguments]; index += 1) {
                const char *argType = [signature getArgumentTypeAtIndex:index];
                [argTypes addObject:argType ? [NSString stringWithUTF8String:argType] : @""];
            }
            debug[@"signature_arg_types"] = argTypes;
            const char *returnType = [signature methodReturnType];
            debug[@"signature_return_type"] = returnType ? [NSString stringWithUTF8String:returnType] : @"";
        }
        fprintf(stderr, "probe:signature=%s\n", signature ? "yes" : "no");
        fflush(stderr);
        if (!signature) {
            debug[@"invoke_error"] = @"missing send signature";
            NSData *json = [NSJSONSerialization dataWithJSONObject:debug options:NSJSONWritingPrettyPrinted error:nil];
            fwrite([json bytes], 1, [json length], stdout);
            fputc('\n', stdout);
            return 1;
        }

        id message = nil;
        if ([carrier isEqualToString:@"immessage"]) {
            message = BuildIMMessage(sender, text, [threadIdentifier length] ? threadIdentifier : nil, debug);
            SetObjectProperty(message, @"setReplyToGUID:", replyGuid);
        } else if ([carrier isEqualToString:@"associateditem"]) {
            message = BuildAssociatedMessageItem(
                sender,
                identifier,
                accountID,
                service,
                text,
                [parentGuid length] ? parentGuid : identifier,
                [threadIdentifier length] ? threadIdentifier : nil,
                replyGuid,
                debug
            );
        } else if ([carrier isEqualToString:@"messageitem"]) {
            message = BuildMessageItem(
                sender,
                identifier,
                accountID,
                service,
                text,
                [threadIdentifier length] ? threadIdentifier : nil,
                replyGuid,
                debug
            );
        } else {
            message = BuildSimulatedMessage(chatGuid, identifier, sender, text, threadIdentifier, debug);
        }
        debug[@"message_class"] = NSStringFromClass([message class]) ?: @"";
        debug[@"message_reply_to_guid"] = StringProp(message, @"replyToGUID");
        debug[@"message_thread_identifier"] = StringProp(message, @"threadIdentifier");
        id payloadObject = PayloadForShape(message, payloadShape, debug);
        debug[@"payload_class"] = NSStringFromClass([payloadObject class]) ?: @"";
        fprintf(stderr, "probe:message=%s\n", [Describe(message) UTF8String]);
        fflush(stderr);
        if (!payloadObject) {
            NSData *json = [NSJSONSerialization dataWithJSONObject:debug options:NSJSONWritingPrettyPrinted error:nil];
            fwrite([json bytes], 1, [json length], stdout);
            fputc('\n', stdout);
            return 1;
        }

        NSString *chatArg = [chatGuid length] ? chatGuid : nil;
        NSString *identifierArg = [identifier length] ? identifier : nil;
        id accountArg = [accountID length] ? accountID : nil;

        @try {
            NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:signature];
            [invocation setTarget:proxy];
            [invocation setSelector:sendSel];
            [invocation setArgument:&payloadObject atIndex:2];
            [invocation setArgument:&chatArg atIndex:3];
            [invocation setArgument:&identifierArg atIndex:4];

            const char *styleType = [signature getArgumentTypeAtIndex:5];
            if (styleType && styleType[0] == 'q') {
                long long styleArg = (long long)styleValue;
                [invocation setArgument:&styleArg atIndex:5];
                debug[@"style_arg_type"] = @"q";
            } else {
                int styleArg = (int)styleValue;
                [invocation setArgument:&styleArg atIndex:5];
                debug[@"style_arg_type"] = styleType ? [NSString stringWithUTF8String:styleType] : @"";
            }

            [invocation setArgument:&accountArg atIndex:6];
            fprintf(stderr, "probe:invoke-begin\n");
            fflush(stderr);
            [invocation invoke];
            fprintf(stderr, "probe:invoke-end\n");
            fflush(stderr);
            debug[@"invoked"] = @YES;
        } @catch (NSException *exc) {
            debug[@"invoke_exception"] = Describe(exc);
            fprintf(stderr, "probe:invoke-exception=%s\n", [Describe(exc) UTF8String]);
            fflush(stderr);
        }

        for (NSInteger i = 0; i < 40; i += 1) {
            [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.15]];
        }
        fprintf(stderr, "probe:done\n");
        fflush(stderr);

        NSData *json = [NSJSONSerialization dataWithJSONObject:debug options:NSJSONWritingPrettyPrinted error:nil];
        if (json) {
            fwrite([json bytes], 1, [json length], stdout);
            fputc('\n', stdout);
        }
    }
    return 0;
}
