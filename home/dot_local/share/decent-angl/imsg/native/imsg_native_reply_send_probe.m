#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>
#import <objc/runtime.h>

typedef id (*CopyMessagesForGUIDsFn)(CFArrayRef);
typedef id (*CreateIMItemWithAccountLookupFn)(id, id, BOOL, id);
typedef void (*SetDBServerProcessFn)(int);

static NSString *StringProp(id target, NSString *name);

static NSString *const kSpoofedBundleID = @"com.apple.iChat";
static NSString *const kListenerID = @"com.decentangl.imsg.native-reply";
static const unsigned int kListenerCapabilities = 2162567U;
static IMP gOriginalBundleIdentifierImp = NULL;
static NSDictionary *gDaemonSetupInfo = nil;
static NSNumber *gDaemonSetupSuccess = nil;
static NSString *gLastSentAccountID = nil;
static NSString *gLastSentChatIdentifier = nil;
static NSString *gLastSentMessageGUID = nil;

@interface ProbeDaemonListener : NSObject
@end

@implementation ProbeDaemonListener

- (void)setupComplete:(BOOL)success info:(NSDictionary *)info {
    gDaemonSetupSuccess = @(success);
    gDaemonSetupInfo = [info copy];
}

- (void)chatLoadedWithChatIdentifier:(NSString *)chatIdentifier chats:(NSArray *)chats {
    if (chatIdentifier.length) {
        gLastSentChatIdentifier = [chatIdentifier copy];
    }
}

- (void)account:(NSString *)accountUniqueID
           chat:(NSString *)chatIdentifier
          style:(unsigned char)chatStyle
 chatProperties:(NSDictionary *)properties
notifySentMessage:(id)message
       sendTime:(NSNumber *)sendTime {
    gLastSentAccountID = [accountUniqueID copy];
    gLastSentChatIdentifier = [chatIdentifier copy];
    gLastSentMessageGUID = StringProp(message, @"guid");
}

@end

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

static BOOL CallBool0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return NO;
    }
    return ((BOOL(*)(id, SEL))objc_msgSend)(target, sel);
}

static unsigned long long CallULL0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return 0;
    }
    return ((unsigned long long(*)(id, SEL))objc_msgSend)(target, sel);
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

static void CallVoidBool1(id target, NSString *name, BOOL value) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, BOOL))objc_msgSend)(target, sel, value);
}

static void CallVoidULL1(id target, NSString *name, unsigned long long value) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return;
    }
    ((void(*)(id, SEL, unsigned long long))objc_msgSend)(target, sel, value);
}

static NSString *StringProp(id target, NSString *name) {
    id value = Call0(target, name);
    if ([value isKindOfClass:[NSString class]]) {
        return value;
    }
    return Describe(value);
}

static void RunLoopSleep(NSTimeInterval seconds) {
    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:seconds]];
}

static NSString *SwizzledBundleIdentifier(id self, SEL _cmd) {
    if (self == [NSBundle mainBundle]) {
        return kSpoofedBundleID;
    }
    if (!gOriginalBundleIdentifierImp) {
        return @"";
    }
    return ((NSString *(*)(id, SEL))gOriginalBundleIdentifierImp)(self, _cmd);
}

static void InstallBundleIDSpoof(void) {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        Method method = class_getInstanceMethod([NSBundle class], @selector(bundleIdentifier));
        gOriginalBundleIdentifierImp = method_getImplementation(method);
        method_setImplementation(method, (IMP)SwizzledBundleIdentifier);
    });
}

static BOOL AddListenerID(id daemon, NSMutableDictionary *payload) {
    SEL sel = NSSelectorFromString(@"addListenerID:capabilities:");
    if (!daemon || !sel || ![daemon respondsToSelector:sel]) {
        return NO;
    }
    @try {
        ((void(*)(id, SEL, id, unsigned int))objc_msgSend)(daemon, sel, kListenerID, kListenerCapabilities);
        payload[@"listener_id"] = kListenerID;
        payload[@"listener_capabilities"] = @(kListenerCapabilities);
        return YES;
    } @catch (NSException *exc) {
        payload[@"listener_exception"] = Describe(exc);
        return NO;
    }
}

static BOOL AddDaemonHandler(id daemon, id handler, NSMutableDictionary *payload) {
    id listener = Call0(daemon, @"listener");
    payload[@"daemon_listener"] = Describe(listener);
    SEL sel = NSSelectorFromString(@"addHandler:");
    if (!listener || !sel || ![listener respondsToSelector:sel]) {
        return NO;
    }
    @try {
        ((void(*)(id, SEL, id))objc_msgSend)(listener, sel, handler);
        return YES;
    } @catch (NSException *exc) {
        payload[@"daemon_listener_exception"] = Describe(exc);
        return NO;
    }
}

static BOOL ConnectDaemon(id daemon, unsigned long long capabilities, NSMutableDictionary *payload) {
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

    SEL blockSel = NSSelectorFromString(@"blockUntilConnected");
    if (daemon && blockSel && [daemon respondsToSelector:blockSel]) {
        @try {
            ((void(*)(id, SEL))objc_msgSend)(daemon, blockSel);
            payload[@"daemon_connect_selector"] = @"blockUntilConnected";
            return YES;
        } @catch (NSException *exc) {
            payload[@"daemon_connect_exception"] = Describe(exc);
        }
    }
    return NO;
}

static NSDictionary *DumpPartItem(id part) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!part) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([part class]) ?: @"";
    payload[@"description"] = Describe(part);
    payload[@"index"] = Describe(Call0(part, @"index"));
    payload[@"text"] = Describe(Call0(part, @"text"));
    payload[@"threadIdentifier"] = StringProp(part, @"threadIdentifier") ?: @"";
    payload[@"threadOriginator"] = Describe(Call0(part, @"threadOriginator")) ?: @"";
    payload[@"messagePartRange"] = Describe(Call0(part, @"messagePartRange")) ?: @"";
    payload[@"guid"] = StringProp(Call0(part, @"_item"), @"guid") ?: @"";
    return payload;
}

static NSArray *DumpChatItems(id container) {
    NSMutableArray *items = [NSMutableArray array];
    if (!container) {
        return items;
    }
    if ([container isKindOfClass:[NSArray class]]) {
        for (id entry in (NSArray *)container) {
            [items addObject:DumpPartItem(entry)];
        }
        return items;
    }
    [items addObject:DumpPartItem(container)];
    return items;
}

static NSDictionary *DumpMessageLike(id message) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!message) {
        return payload;
    }
    payload[@"class"] = NSStringFromClass([message class]) ?: @"";
    payload[@"description"] = Describe(message);
    payload[@"guid"] = StringProp(message, @"guid") ?: @"";
    payload[@"text"] = Describe(Call0(message, @"text")) ?: @"";
    payload[@"plainBody"] = StringProp(message, @"plainBody") ?: @"";
    payload[@"threadIdentifier"] = StringProp(message, @"threadIdentifier") ?: @"";
    payload[@"replyToGUID"] = StringProp(message, @"replyToGUID") ?: @"";
    payload[@"threadOriginator"] = Describe(Call0(message, @"threadOriginator")) ?: @"";
    payload[@"_imMessageItem"] = Describe(Call0(message, @"_imMessageItem")) ?: @"";
    return payload;
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
    payload[@"service"] = StringProp(item, @"service") ?: @"";
    payload[@"accountID"] = StringProp(item, @"accountID") ?: @"";
    payload[@"isFromMe"] = @(CallBool0(item, @"isFromMe"));
    payload[@"plainBody"] = StringProp(item, @"plainBody") ?: @"";
    payload[@"body"] = Describe(Call0(item, @"body")) ?: @"";
    payload[@"threadIdentifier"] = StringProp(item, @"threadIdentifier") ?: @"";
    payload[@"threadOriginator"] = Describe(Call0(item, @"threadOriginator")) ?: @"";

    id newChatItems = Call0(item, @"_newChatItems");
    payload[@"_newChatItems"] = DumpChatItems(newChatItems);
    return payload;
}

static NSDictionary *LoadPersistenceItem(NSString *guid, CopyMessagesForGUIDsFn copyFn, CreateIMItemWithAccountLookupFn accountFn, SetDBServerProcessFn setDbFn) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (!guid.length || !copyFn || !accountFn || !setDbFn) {
        return payload;
    }

    setDbFn(1);
    NSArray *guids = @[guid];
    id refs = copyFn((__bridge CFArrayRef)guids);
    payload[@"refs_count"] = @([refs respondsToSelector:@selector(count)] ? [refs count] : 0);
    payload[@"refs_description"] = Describe(refs);
    id ref = [refs respondsToSelector:@selector(firstObject)] ? [refs firstObject] : nil;
    payload[@"first_ref"] = Describe(ref);
    id item = nil;
    if (ref) {
        @try {
            item = accountFn(ref, nil, NO, nil);
        } @catch (NSException *exc) {
            payload[@"create_item_exception"] = Describe(exc);
        }
    }
    payload[@"item"] = DumpItem(item);
    return payload;
}

static NSString *ResolveThreadIdentifierFromPersistence(NSDictionary *persistencePayload) {
    NSDictionary *item = persistencePayload[@"item"];
    NSString *threadIdentifier = item[@"threadIdentifier"];
    if ([threadIdentifier isKindOfClass:[NSString class]] && threadIdentifier.length) {
        return threadIdentifier;
    }
    NSArray *chatItems = item[@"_newChatItems"];
    if ([chatItems isKindOfClass:[NSArray class]]) {
        for (NSDictionary *chatItem in chatItems) {
            NSString *candidate = chatItem[@"threadIdentifier"];
            if ([candidate isKindOfClass:[NSString class]] && candidate.length) {
                return candidate;
            }
        }
    }
    return @"";
}

static id ResolveService(NSString *serviceName) {
    Class serviceClass = NSClassFromString(@"IMServiceImpl");
    id service = Call1(serviceClass, @"serviceWithName:", serviceName);
    if (!service) {
        service = Call1(serviceClass, @"serviceWithInternalName:", serviceName);
    }
    return service;
}

static id BuildSyntheticAccount(NSString *accountID, NSString *serviceName, NSString *loginID) {
    if (!accountID.length) {
        return nil;
    }
    id service = ResolveService(serviceName.length ? serviceName : @"iMessage");
    if (!service) {
        return nil;
    }
    Class accountClass = NSClassFromString(@"IMAccount");
    if (!accountClass) {
        return nil;
    }
    id rawAccount = [accountClass alloc];
    SEL initSel = NSSelectorFromString(@"initWithUniqueID:service:");
    if (!rawAccount || !initSel || ![rawAccount respondsToSelector:initSel]) {
        return nil;
    }
    id account = ((id(*)(id, SEL, id, id))objc_msgSend)(rawAccount, initSel, accountID, service);
    if (loginID.length) {
        CallVoid1(account, @"setLogin:", loginID);
        CallVoid1(account, @"setLoginID:", loginID);
        CallVoid1(account, @"setStrippedLogin:", [loginID hasPrefix:@"E:"] ? [loginID substringFromIndex:2] : loginID);
    }
    CallVoidBool1(account, @"setIsActive:", YES);
    CallVoid0(account, @"registerAccount");
    CallVoid0(account, @"loginIfActiveRegistered");
    return account;
}

static id ResolveAccount(id accountController, NSString *accountID) {
    id account = Call0(accountController, @"activeIMessageAccount");
    if (!account) {
        account = Call0(accountController, @"mostLoggedInAccount");
    }
    if (!account && accountID.length) {
        account = Call1(accountController, @"accountForUniqueID:", accountID);
    }
    return account;
}

static id ResolveHandle(id account, NSString *identifier) {
    if (account) {
        id handle = Call1(account, @"imHandleWithID:", identifier);
        if (handle) {
            return handle;
        }
    }

    id registrar = Call0(NSClassFromString(@"IMHandleRegistrar"), @"sharedInstance");
    id handles = Call1(registrar, @"getIMHandlesForID:", identifier);
    if ([handles isKindOfClass:[NSArray class]] && [handles count] > 0) {
        return [handles firstObject];
    }

    Class handleClass = NSClassFromString(@"IMHandle");
    if (!handleClass || !identifier.length) {
        return nil;
    }
    id rawHandle = [handleClass alloc];
    SEL initSel = NSSelectorFromString(@"initWithAccount:ID:alreadyCanonical:");
    if (rawHandle && initSel && [rawHandle respondsToSelector:initSel]) {
        return ((id(*)(id, SEL, id, id, BOOL))objc_msgSend)(rawHandle, initSel, account, identifier, YES);
    }
    return nil;
}

static id ResolveChat(id registry, NSString *chatGuid, id handle, NSMutableDictionary *payload) {
    NSArray<NSString *> *guidSelectors = @[@"existingChatWithGUID:"];
    for (NSString *selectorName in guidSelectors) {
        id chat = Call1(registry, selectorName, chatGuid);
        if (chat) {
            payload[@"chat_selector"] = selectorName;
            return chat;
        }
    }

    NSArray<NSString *> *handleSelectors = @[
        @"existingChatForIMHandle:",
        @"existingChatWithHandle:",
        @"chatForIMHandle:",
        @"chatWithHandle:",
    ];
    for (NSString *selectorName in handleSelectors) {
        id chat = Call1(registry, selectorName, handle);
        if (chat) {
            payload[@"chat_selector"] = selectorName;
            return chat;
        }
    }
    return nil;
}

static id BuildMessageItem(NSString *identifier, NSString *accountID, NSString *service, NSString *text, NSString *threadIdentifier, NSString *replyToGuid) {
    Class itemClass = NSClassFromString(@"IMMessageItem");
    if (!itemClass) {
        return nil;
    }
    SEL initSel = NSSelectorFromString(@"initWithSender:time:body:attributes:fileTransferGUIDs:flags:error:guid:threadIdentifier:");
    if (![itemClass instancesRespondToSelector:initSel]) {
        return nil;
    }

    id instance = [itemClass alloc];
    NSDate *time = [NSDate date];
    NSAttributedString *body = [[NSAttributedString alloc] initWithString:text ?: @""];
    NSDictionary *attributes = @{};
    NSArray *fileTransferGUIDs = @[];
    unsigned long long flags = 0x100005ULL;
    NSString *guid = [[NSUUID UUID] UUIDString];
    id item = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id))objc_msgSend)(
        instance,
        initSel,
        identifier ?: @"",
        time,
        body,
        attributes,
        fileTransferGUIDs,
        flags,
        nil,
        guid,
        threadIdentifier ?: @""
    );
    CallVoid1(item, @"setHandle:", identifier);
    CallVoid1(item, @"setSender:", identifier);
    CallVoid1(item, @"setAccountID:", accountID);
    CallVoid1(item, @"setAccount:", accountID);
    CallVoid1(item, @"setService:", service);
    if (replyToGuid.length) {
        CallVoid1(item, @"setReplyToGUID:", replyToGuid);
    }
    return item;
}

static id BuildOutgoingMessage(NSString *identifier, NSString *accountID, NSString *service, NSString *text, NSString *threadIdentifier, NSString *replyToGuid, NSString *payloadKind) {
    if (![payloadKind isEqualToString:@"immessage"]) {
        id item = BuildMessageItem(identifier, accountID, service, text, threadIdentifier, replyToGuid);
        if (item) {
            return item;
        }
    }

    Class messageClass = NSClassFromString(@"IMMessage");
    if (!messageClass) {
        return nil;
    }
    NSAttributedString *content = [[NSAttributedString alloc] initWithString:text ?: @""];
    SEL factorySel = NSSelectorFromString(@"instantMessageWithText:messageSubject:fileTransferGUIDs:flags:threadIdentifier:");
    id message = nil;
    if ([messageClass respondsToSelector:factorySel]) {
        message = ((id(*)(id, SEL, id, id, id, unsigned long long, id))objc_msgSend)(
            messageClass,
            factorySel,
            content,
            nil,
            @[],
            0x100005ULL,
            threadIdentifier
        );
    } else {
        message = [messageClass new];
        SEL initSel = NSSelectorFromString(@"initWithSender:time:text:messageSubject:fileTransferGUIDs:flags:error:guid:subject:balloonBundleID:payloadData:expressiveSendStyleID:");
        if (message && initSel && [message respondsToSelector:initSel]) {
            message = ((id(*)(id, SEL, id, id, id, id, id, unsigned long long, id, id, id, id, id, id))objc_msgSend)(
                message,
                initSel,
                nil,
                nil,
                content,
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
            CallVoid1(message, @"setThreadIdentifier:", threadIdentifier);
        }
    }
    if (replyToGuid.length) {
        CallVoid1(message, @"setReplyToGUID:", replyToGuid);
    }
    return message;
}

static BOOL SendMessage(id registry, id chat, id account, id message, NSString *replyGuid, NSMutableDictionary *payload) {
    if (!chat || !message) {
        return NO;
    }
    BOOL isMessageItem = [NSStringFromClass([message class]) hasSuffix:@"MessageItem"];

    if (replyGuid.length && registry && [registry respondsToSelector:NSSelectorFromString(@"_setReplyToGuidOnMessage:forChat:")]) {
        @try {
            ((void(*)(id, SEL, id, id))objc_msgSend)(registry, NSSelectorFromString(@"_setReplyToGuidOnMessage:forChat:"), message, chat);
            payload[@"set_reply_selector"] = @"_setReplyToGuidOnMessage:forChat:";
        } @catch (NSException *exc) {
            payload[@"set_reply_exception"] = Describe(exc);
        }
    }

    CallVoid0(chat, @"refreshServiceForSending");

    NSArray<NSString *> *chatSelectors = isMessageItem
        ? @[@"sendMessage:onAccount:", @"sendMessage:withAccount:"]
        : @[@"sendMessage:onAccount:", @"sendMessage:withAccount:", @"sendMessage:"];
    for (NSString *selectorName in chatSelectors) {
        SEL sel = NSSelectorFromString(selectorName);
        if (![chat respondsToSelector:sel]) {
            continue;
        }
        @try {
            if (([selectorName isEqualToString:@"sendMessage:onAccount:"] || [selectorName isEqualToString:@"sendMessage:withAccount:"]) && account) {
                ((void(*)(id, SEL, id, id))objc_msgSend)(chat, sel, message, account);
                payload[@"send_selector"] = selectorName;
                return YES;
            }
            if ([selectorName isEqualToString:@"sendMessage:"]) {
                ((void(*)(id, SEL, id))objc_msgSend)(chat, sel, message);
                payload[@"send_selector"] = selectorName;
                return YES;
            }
        } @catch (NSException *exc) {
            payload[[NSString stringWithFormat:@"%@_exception", selectorName]] = Describe(exc);
        }
    }

    if (registry && account && [registry respondsToSelector:NSSelectorFromString(@"_chat:sendMessage:withAccount:")]) {
        @try {
            ((void(*)(id, SEL, id, id, id))objc_msgSend)(registry, NSSelectorFromString(@"_chat:sendMessage:withAccount:"), chat, message, account);
            payload[@"send_selector"] = @"_chat:sendMessage:withAccount:";
            return YES;
        } @catch (NSException *exc) {
            payload[@"registry_send_with_account_exception"] = Describe(exc);
        }
    }

    if (!isMessageItem && registry && [registry respondsToSelector:NSSelectorFromString(@"_chat:sendMessage:")]) {
        @try {
            ((void(*)(id, SEL, id, id))objc_msgSend)(registry, NSSelectorFromString(@"_chat:sendMessage:"), chat, message);
            payload[@"send_selector"] = @"_chat:sendMessage:";
            return YES;
        } @catch (NSException *exc) {
            payload[@"registry_send_exception"] = Describe(exc);
        }
    }

    return NO;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *chatGuid = ArgValue(args, @"--chat-guid", @"any;-;btuckercraig@gmail.com");
        NSString *identifier = ArgValue(args, @"--identifier", @"btuckercraig@gmail.com");
        NSString *replyGuid = ArgValue(args, @"--reply-guid", @"0C8A316A-CF0E-4FF3-A35E-A8BD7841E429");
        NSString *loginID = ArgValue(args, @"--login-id", @"E:btuckerc.dev@gmail.com");
        NSString *text = ArgValue(args, @"--text", @"");
        NSString *outputPath = ArgValue(args, @"--output", @"");
        NSString *payloadKind = ArgValue(args, @"--payload-kind", @"messageitem");
        unsigned long long capabilities = ArgULL(args, @"--capabilities", 4485895ULL);
        BOOL send = HasFlag(args, @"--send");

        [NSApplication sharedApplication];
        InstallBundleIDSpoof();

        void *imcore = dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        void *imdaemon = dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);
        void *imdpersistence = dlopen("/System/Library/PrivateFrameworks/IMDPersistence.framework/IMDPersistence", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMFoundation.framework/IMFoundation", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMSharedUtilities.framework/IMSharedUtilities", RTLD_LAZY);

        CopyMessagesForGUIDsFn copyFn = (CopyMessagesForGUIDsFn)dlsym(imdpersistence, "IMDMessageRecordCopyMessagesForGUIDs");
        CreateIMItemWithAccountLookupFn accountLookupFn = (CreateIMItemWithAccountLookupFn)dlsym(imdpersistence, "IMDCreateIMItemFromIMDMessageRecordRefWithAccountLookup");
        SetDBServerProcessFn setDbFn = (SetDBServerProcessFn)dlsym(imdpersistence, "IMDSetIsRunningInDatabaseServerProcess");

        NSMutableDictionary *payload = [NSMutableDictionary dictionary];
        payload[@"chat_guid"] = chatGuid ?: @"";
        payload[@"identifier"] = identifier ?: @"";
        payload[@"reply_guid"] = replyGuid ?: @"";
        payload[@"login_id"] = loginID ?: @"";
        payload[@"payload_kind"] = payloadKind ?: @"";
        payload[@"send"] = @(send);
        payload[@"bundle_id_after_spoof"] = [[[NSBundle mainBundle] bundleIdentifier] copy] ?: @"";
        payload[@"dlopen_imcore"] = @(imcore != NULL);
        payload[@"dlopen_imdaemon"] = @(imdaemon != NULL);
        payload[@"dlopen_imdpersistence"] = @(imdpersistence != NULL);
        payload[@"requested_capabilities"] = @(capabilities);

        if (setDbFn) {
            setDbFn(1);
            payload[@"set_db_process"] = @YES;
        } else {
            payload[@"set_db_process"] = @NO;
        }

        id daemonClass = NSClassFromString(@"IMDaemonController");
        id daemon = Call0(daemonClass, @"sharedController");
        if (!daemon) {
            daemon = Call0(daemonClass, @"sharedInstance");
        }
        if (!daemon) {
            daemon = Call0(daemonClass, @"shared");
        }
        payload[@"daemon"] = Describe(daemon);
        payload[@"daemon_process_capabilities_before"] = @(CallULL0(daemon, @"processCapabilities"));
        CallVoidULL1(daemon, @"setProcessCapabilities:", capabilities);
        payload[@"daemon_process_capabilities_after"] = @(CallULL0(daemon, @"processCapabilities"));
        id daemonHandler = [ProbeDaemonListener new];
        payload[@"daemon_handler_added"] = @(AddDaemonHandler(daemon, daemonHandler, payload));
        payload[@"listener_added"] = @(AddListenerID(daemon, payload));
        payload[@"daemon_connect_result"] = @(ConnectDaemon(daemon, capabilities, payload));
        payload[@"daemon_process_context"] = Describe(Call0(daemon, @"processContext")) ?: @"";
        CallVoid0(daemon, @"loadAllChats");
        RunLoopSleep(2.0);
        payload[@"daemon_setup_success"] = gDaemonSetupSuccess ?: [NSNull null];
        payload[@"daemon_setup_info"] = Describe(gDaemonSetupInfo) ?: @"";

        id accountController = Call0(NSClassFromString(@"IMAccountController"), @"sharedInstance");
        NSArray *accounts = Call0(accountController, @"accounts");
        payload[@"account_controller"] = Describe(accountController);
        payload[@"accounts_count"] = @([accounts isKindOfClass:[NSArray class]] ? [accounts count] : 0);
        payload[@"accounts"] = Describe(accounts) ?: @"";

        NSDictionary *persistence = LoadPersistenceItem(replyGuid, copyFn, accountLookupFn, setDbFn);
        payload[@"persistence"] = persistence;
        NSString *threadIdentifier = ResolveThreadIdentifierFromPersistence(persistence);
        payload[@"derived_thread_identifier"] = threadIdentifier ?: @"";

        NSString *accountID = persistence[@"item"][@"accountID"];
        NSString *serviceName = persistence[@"item"][@"service"];
        id account = ResolveAccount(accountController, accountID);
        if (!account) {
            account = BuildSyntheticAccount(accountID, serviceName, loginID);
        }
        id sendAccount = account ?: accountID;
        payload[@"resolved_account"] = Describe(account);
        payload[@"resolved_account_service"] = Describe(Call0(account, @"service"));
        payload[@"resolved_account_login"] = StringProp(account, @"login") ?: @"";
        payload[@"send_account"] = Describe(sendAccount);

        if (account && [accounts isKindOfClass:[NSArray class]]) {
            for (id candidate in accounts) {
                CallVoidULL1(candidate, @"updateCapabilities:", ULLONG_MAX);
            }
            RunLoopSleep(0.5);
        }

        id handle = ResolveHandle(account, identifier);
        payload[@"handle"] = Describe(handle);
        payload[@"handle_id"] = StringProp(handle, @"ID") ?: @"";

        id registry = Call0(NSClassFromString(@"IMChatRegistry"), @"sharedInstance");
        payload[@"registry"] = Describe(registry);
        id chat = ResolveChat(registry, chatGuid, handle, payload);
        payload[@"chat"] = Describe(chat);
        payload[@"chat_guid_runtime"] = StringProp(chat, @"guid") ?: @"";
        payload[@"chat_identifier"] = StringProp(chat, @"chatIdentifier") ?: @"";
        payload[@"chat_account"] = Describe(Call0(chat, @"account")) ?: @"";
        payload[@"chat_has_had_successful_query"] = @(CallBool0(chat, @"hasHadSuccessfulQuery"));
        payload[@"chat_can_send"] = @(CallBool0(chat, @"canSend"));
        payload[@"chat_can_send_inline_reply"] = @(CallBool0(chat, @"canSendInlineReply"));

        if (send && text.length && chat && threadIdentifier.length) {
            id outgoing = BuildOutgoingMessage(identifier, accountID, @"iMessage", text, threadIdentifier, replyGuid, payloadKind);
            payload[@"outgoing"] = DumpMessageLike(outgoing);
            payload[@"send_invoked"] = @(SendMessage(registry, chat, sendAccount, outgoing, replyGuid, payload));
            RunLoopSleep(4.0);
            payload[@"chat_last_message"] = DumpMessageLike(Call0(chat, @"lastMessage"));
            payload[@"chat_last_sent_message"] = DumpMessageLike(Call0(chat, @"lastSentMessage"));
            payload[@"daemon_last_sent_account_id"] = gLastSentAccountID ?: @"";
            payload[@"daemon_last_sent_chat_identifier"] = gLastSentChatIdentifier ?: @"";
            payload[@"daemon_last_sent_message_guid"] = gLastSentMessageGUID ?: @"";
        }

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        if (outputPath.length) {
            [json writeToFile:outputPath atomically:YES];
        } else {
            fwrite([json bytes], 1, [json length], stdout);
            fputc('\n', stdout);
        }
    }
    return 0;
}
