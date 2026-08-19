#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>
#import <objc/runtime.h>
#import <unistd.h>

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

int main(void) {
    @autoreleasepool {
        fprintf(stderr, "probe:start\n");
        fflush(stderr);
        [NSApplication sharedApplication];
        fprintf(stderr, "probe:nsapp\n");
        fflush(stderr);
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);
        fprintf(stderr, "probe:dlopen\n");
        fflush(stderr);

        Class daemonClass = NSClassFromString(@"IMDaemonController");
        Class accountClass = NSClassFromString(@"IMAccountController");
        Class registryClass = NSClassFromString(@"IMChatRegistry");
        fprintf(stderr, "probe:classes daemon=%s account=%s registry=%s\n",
                daemonClass ? class_getName(daemonClass) : "(null)",
                accountClass ? class_getName(accountClass) : "(null)",
                registryClass ? class_getName(registryClass) : "(null)");
        fflush(stderr);

        id daemon = Call0(daemonClass, @"sharedInstance");
        fprintf(stderr, "probe:daemon=%s\n", [Describe(daemon) UTF8String]);
        fflush(stderr);
        CallVoid0(daemon, @"blockUntilConnected");
        fprintf(stderr, "probe:connected\n");
        fflush(stderr);
        CallVoid0(daemon, @"loadAllChats");
        fprintf(stderr, "probe:loadAllChats\n");
        fflush(stderr);

        for (NSInteger i = 0; i < 20; i += 1) {
            [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.25]];
        }
        fprintf(stderr, "probe:runloop\n");
        fflush(stderr);

        id accountController = Call0(accountClass, @"sharedInstance");
        id accounts = Call0(accountController, @"activeAccounts");
        id activeIMessageAccount = Call0(accountController, @"activeIMessageAccount");
        id chatRegistry = Call0(registryClass, @"sharedInstance");
        id chats = Call0(chatRegistry, @"allExistingChats");

        NSDictionary *payload = @{
            @"daemon_class": daemonClass ? NSStringFromClass(daemonClass) : @"",
            @"daemon": Describe(daemon),
            @"account_controller": Describe(accountController),
            @"accounts_class": accounts ? NSStringFromClass([accounts class]) : @"",
            @"accounts": Describe(accounts),
            @"active_imessage_account": Describe(activeIMessageAccount),
            @"chat_registry": Describe(chatRegistry),
            @"chats_class": chats ? NSStringFromClass([chats class]) : @"",
            @"chats": Describe(chats),
        };

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        if (json) {
            write(STDOUT_FILENO, [json bytes], [json length]);
            write(STDOUT_FILENO, "\n", 1);
        }
        fprintf(stderr, "probe:done\n");
        fflush(stderr);
    }
    return 0;
}
