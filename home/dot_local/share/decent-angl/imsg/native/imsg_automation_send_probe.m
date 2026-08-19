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

static NSMutableArray<NSString *> *SignatureArgs(NSMethodSignature *signature) {
    NSMutableArray<NSString *> *types = [NSMutableArray array];
    for (NSUInteger index = 0; index < [signature numberOfArguments]; index += 1) {
        const char *argType = [signature getArgumentTypeAtIndex:index];
        [types addObject:argType ? [NSString stringWithUTF8String:argType] : @""];
    }
    return types;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *text = ArgValue(args, @"--text", @"probe");
        NSString *destination = ArgValue(args, @"--destination", @"btuckercraig@gmail.com");
        NSString *service = ArgValue(args, @"--service", @"iMessage");
        NSString *threadIdentifier = ArgValue(args, @"--thread-id", @"");
        BOOL invoke = [args containsObject:@"--invoke"];
        BOOL activateMessages = [args containsObject:@"--activate-messages"];

        NSMutableDictionary *debug = [NSMutableDictionary dictionary];
        debug[@"text"] = text ?: @"";
        debug[@"destination"] = destination ?: @"";
        debug[@"service"] = service ?: @"";
        debug[@"thread_identifier"] = threadIdentifier ?: @"";
        debug[@"invoke"] = @(invoke);
        debug[@"activate_messages"] = @(activateMessages);

        [NSApplication sharedApplication];
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);

        if (activateMessages) {
            NSURL *messagesURL = [NSURL fileURLWithPath:@"/System/Applications/Messages.app"];
            NSError *launchError = nil;
            [[NSWorkspace sharedWorkspace] launchApplicationAtURL:messagesURL
                                                          options:NSWorkspaceLaunchDefault
                                                    configuration:@{}
                                                            error:&launchError];
            debug[@"activate_error"] = launchError ? Describe(launchError) : @"";
            for (NSInteger i = 0; i < 20; i += 1) {
                [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.2]];
            }
        }

        Class senderClass = NSClassFromString(@"IMAutomationMessageSend");
        id sender = [senderClass new];
        debug[@"sender_class"] = senderClass ? NSStringFromClass(senderClass) : @"";
        debug[@"sender"] = Describe(sender);

        SEL simpleSel = NSSelectorFromString(@"sendMessage:destinationID:timeOut:threadIdentifier:error:");
        SEL fullSel = NSSelectorFromString(@"sendMessage:destinationID:filePaths:isAudioMessage:groupID:bundleID:attributionInfoName:service:timeOut:threadIdentifier:error:");

        NSMethodSignature *simpleSig = [sender methodSignatureForSelector:simpleSel];
        NSMethodSignature *fullSig = [sender methodSignatureForSelector:fullSel];
        debug[@"simple_signature"] = simpleSig ? [simpleSig debugDescription] : @"";
        debug[@"simple_arg_types"] = simpleSig ? SignatureArgs(simpleSig) : @[];
        debug[@"full_signature"] = fullSig ? [fullSig debugDescription] : @"";
        debug[@"full_arg_types"] = fullSig ? SignatureArgs(fullSig) : @[];

        if (invoke && fullSig) {
            NSError *error = nil;
            NSArray *files = @[];
            NSString *groupID = nil;
            NSString *bundleID = nil;
            NSString *attributionName = nil;
            BOOL isAudioMessage = NO;
            double timeoutValue = 15.0;
            NSString *threadArg = [threadIdentifier length] ? threadIdentifier : nil;
            @try {
                NSInvocation *invocation = [NSInvocation invocationWithMethodSignature:fullSig];
                [invocation setTarget:sender];
                [invocation setSelector:fullSel];
                [invocation setArgument:&text atIndex:2];
                [invocation setArgument:&destination atIndex:3];
                [invocation setArgument:&files atIndex:4];
                [invocation setArgument:&isAudioMessage atIndex:5];
                [invocation setArgument:&groupID atIndex:6];
                [invocation setArgument:&bundleID atIndex:7];
                [invocation setArgument:&attributionName atIndex:8];
                [invocation setArgument:&service atIndex:9];
                [invocation setArgument:&timeoutValue atIndex:10];
                [invocation setArgument:&threadArg atIndex:11];
                [invocation setArgument:&error atIndex:12];
                [invocation invoke];

                __unsafe_unretained id returnValue = nil;
                if (strcmp([fullSig methodReturnType], "@") == 0) {
                    [invocation getReturnValue:&returnValue];
                }
                debug[@"invoke_return"] = Describe(returnValue);
                debug[@"invoke_error"] = error ? Describe(error) : @"";
            } @catch (NSException *exc) {
                debug[@"invoke_exception"] = Describe(exc);
            }
        }

        NSData *json = [NSJSONSerialization dataWithJSONObject:debug options:NSJSONWritingPrettyPrinted error:nil];
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
