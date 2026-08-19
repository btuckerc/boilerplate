#import <Cocoa/Cocoa.h>

__attribute__((constructor))
static void imsg_inject_probe_init(void) {
    @autoreleasepool {
        NSString *bundleID = [[NSBundle mainBundle] bundleIdentifier] ?: @"";
        NSString *path = @"/tmp/imsg-inject-probe.log";
        NSString *line = [NSString stringWithFormat:@"loaded bundle=%@ pid=%d\n", bundleID, [[NSProcessInfo processInfo] processIdentifier]];
        NSFileHandle *handle = [NSFileHandle fileHandleForWritingAtPath:path];
        if (!handle) {
            [line writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];
            return;
        }
        @try {
            [handle seekToEndOfFile];
            [handle writeData:[line dataUsingEncoding:NSUTF8StringEncoding]];
        } @catch (__unused NSException *exc) {
        }
        [handle closeFile];
    }
}
