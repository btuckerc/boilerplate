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

static id Call0(id target, NSString *name) {
    SEL sel = NSSelectorFromString(name);
    if (!target || !sel || ![target respondsToSelector:sel]) {
        return nil;
    }
    return ((id(*)(id, SEL))objc_msgSend)(target, sel);
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

static id ConfigureDaemonContext(id daemon, unsigned long long capabilities) {
    SEL sel = NSSelectorFromString(@"multiplexedConnectionWithLabel:capabilities:context:");
    if (!daemon || !sel || ![daemon respondsToSelector:sel]) {
        return nil;
    }
    NSString *bundleID = [[NSBundle mainBundle] bundleIdentifier] ?: @"com.decentangl.imsg-native-probe";
    NSDictionary *context = @{
        @"bundleIdentifier": bundleID,
        @"bundleID": bundleID,
        @"processName": [[NSProcessInfo processInfo] processName] ?: @"",
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
        if (connection) {
            CallVoid1(daemon, @"setAnonymousMultiplexedConnection:", connection);
        }
        return connection;
    } @catch (__unused NSException *exc) {
        return nil;
    }
}

static BOOL InvokeDaemonConnect(id daemon, unsigned long long capabilities) {
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
            return result;
        } @catch (__unused NSException *exc) {
            return NO;
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
        unsigned long long capabilities = ArgULL(args, @"--capabilities", 4485895ULL);
        BOOL activateMessages = [args containsObject:@"--activate-messages"];

        [NSApplication sharedApplication];
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);

        id daemon = Call0(NSClassFromString(@"IMDaemonController"), @"sharedController");
        if (!daemon) {
            daemon = Call0(NSClassFromString(@"IMDaemonController"), @"sharedInstance");
        }
        unsigned long long capsBefore = CallULL0(daemon, @"processCapabilities");
        CallVoidULL1(daemon, @"setProcessCapabilities:", capabilities);
        id customConnection = ConfigureDaemonContext(daemon, capabilities);
        BOOL connected = InvokeDaemonConnect(daemon, capabilities);

        if (activateMessages) {
            NSURL *messagesURL = [NSURL fileURLWithPath:@"/System/Applications/Messages.app"];
            [[NSWorkspace sharedWorkspace] launchApplicationAtURL:messagesURL
                                                          options:NSWorkspaceLaunchDefault
                                                    configuration:@{}
                                                            error:nil];
            for (NSInteger i = 0; i < 20; i += 1) {
                [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.2]];
            }
        }

        id hook = [NSClassFromString(@"IMCoreAutomationHook") new];
        NSError *error = nil;
        NSMutableArray *handles = [NSMutableArray array];
        NSMutableArray *chatResults = [NSMutableArray array];
        NSMutableArray *existingResults = [NSMutableArray array];

        id bestAccount = Call0(hook, @"bestiMessageAccount");
        id handleReturn = ((id(*)(id, SEL, id, NSError **, id))objc_msgSend)(
            hook,
            NSSelectorFromString(@"handlesFromStrings:error:results:"),
            @[identifier],
            &error,
            handles
        );
        NSString *handlesError = Describe(error);
        error = nil;
        id chatReturn = ((id(*)(id, SEL, id, NSError **, id))objc_msgSend)(
            hook,
            NSSelectorFromString(@"chatForHandles:error:results:"),
            handles,
            &error,
            chatResults
        );
        NSString *chatError = Describe(error);
        error = nil;
        id existingReturn = ((id(*)(id, SEL, id, NSError **, id))objc_msgSend)(
            hook,
            NSSelectorFromString(@"existingChatForGroupID:error:results:"),
            chatGuid,
            &error,
            existingResults
        );
        NSString *existingError = Describe(error);

        NSDictionary *payload = @{
            @"daemon": Describe(daemon),
            @"daemon_process_capabilities_before": @(capsBefore),
            @"daemon_process_capabilities_after": @(CallULL0(daemon, @"processCapabilities")),
            @"daemon_process_context": Describe(Call0(daemon, @"processContext")),
            @"daemon_connect_result": @(connected),
            @"daemon_custom_connection": Describe(customConnection),
            @"requested_capabilities": @(capabilities),
            @"best_account": Describe(bestAccount),
            @"hook": Describe(hook),
            @"handles_return": Describe(handleReturn),
            @"handles_error": handlesError ?: @"",
            @"handles": Describe(handles),
            @"chat_return": Describe(chatReturn),
            @"chat_error": chatError ?: @"",
            @"chat_results": Describe(chatResults),
            @"existing_return": Describe(existingReturn),
            @"existing_error": existingError ?: @"",
            @"existing_results": Describe(existingResults),
        };
        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
