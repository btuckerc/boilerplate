#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>

typedef id (*CopyMessagesForGUIDsFn)(CFArrayRef);
typedef id (*CreateIMItemWithAccountLookupFn)(id, id, BOOL, id);
typedef id (*CreateIMItemWithServiceResolveFn)(id, id, BOOL, id);
typedef void (*SetDBServerProcessFn)(int);

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

static NSString *StringProp(id target, NSString *name) {
    id value = Call0(target, name);
    if ([value isKindOfClass:[NSString class]]) {
        return value;
    }
    return Describe(value);
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
    payload[@"imAccount"] = Describe(Call0(item, @"imAccount")) ?: @"";
    payload[@"isFromMe"] = @(CallBool0(item, @"isFromMe"));
    payload[@"plainBody"] = StringProp(item, @"plainBody") ?: @"";
    payload[@"text"] = Describe(Call0(item, @"text")) ?: @"";
    payload[@"body"] = Describe(Call0(item, @"body")) ?: @"";
    payload[@"threadIdentifier"] = StringProp(item, @"threadIdentifier") ?: @"";
    payload[@"threadOriginator"] = Describe(Call0(item, @"threadOriginator")) ?: @"";

    id message = Call0(item, @"message");
    payload[@"message"] = Describe(message);
    payload[@"message_guid"] = StringProp(message, @"guid") ?: @"";
    payload[@"message_threadIdentifier"] = StringProp(message, @"threadIdentifier") ?: @"";
    payload[@"message_replyToGUID"] = StringProp(message, @"replyToGUID") ?: @"";
    payload[@"message_plainBody"] = StringProp(message, @"plainBody") ?: @"";
    payload[@"message_text"] = Describe(Call0(message, @"text")) ?: @"";
    payload[@"message_body"] = Describe(Call0(message, @"body")) ?: @"";

    id newChatItems = Call0(item, @"_newChatItems");
    if (!newChatItems) {
        newChatItems = Call0(message, @"_newChatItems");
    }
    payload[@"_newChatItems"] = DumpChatItems(newChatItems);
    return payload;
}

static NSDictionary *RunQuery(NSString *guid, CopyMessagesForGUIDsFn copyFn, CreateIMItemWithAccountLookupFn accountFn, CreateIMItemWithServiceResolveFn serviceFn, SetDBServerProcessFn setDbFn, int dbMode) {
    NSMutableDictionary *payload = [NSMutableDictionary dictionary];
    if (setDbFn) {
        setDbFn(dbMode);
    }

    NSArray *guids = guid.length ? @[guid] : @[];
    id refs = copyFn ? copyFn((__bridge CFArrayRef)guids) : nil;
    payload[@"db_mode"] = @(dbMode);
    payload[@"refs_description"] = Describe(refs);
    payload[@"refs_count"] = @([refs respondsToSelector:@selector(count)] ? [refs count] : 0);

    id firstRef = ([refs respondsToSelector:@selector(firstObject)] ? [refs firstObject] : nil);
    payload[@"first_ref"] = Describe(firstRef);

    id accountItem = nil;
    if (firstRef && accountFn) {
        @try {
            accountItem = accountFn(firstRef, nil, NO, nil);
        } @catch (NSException *exc) {
            payload[@"account_lookup_exception"] = Describe(exc);
        }
    }
    payload[@"account_lookup_item"] = DumpItem(accountItem);

    id serviceItem = nil;
    if (firstRef && serviceFn) {
        @try {
            serviceItem = serviceFn(firstRef, nil, NO, nil);
        } @catch (NSException *exc) {
            payload[@"service_resolve_exception"] = Describe(exc);
        }
    }
    payload[@"service_resolve_item"] = DumpItem(serviceItem);

    return payload;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *guid = ArgValue(args, @"--guid", @"0C8A316A-CF0E-4FF3-A35E-A8BD7841E429");

        void *imdpersistence = dlopen("/System/Library/PrivateFrameworks/IMDPersistence.framework/IMDPersistence", RTLD_LAZY);
        void *imcore = dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        void *imshared = dlopen("/System/Library/PrivateFrameworks/IMSharedUtilities.framework/IMSharedUtilities", RTLD_LAZY);

        CopyMessagesForGUIDsFn copyFn = (CopyMessagesForGUIDsFn)dlsym(imdpersistence, "IMDMessageRecordCopyMessagesForGUIDs");
        CreateIMItemWithAccountLookupFn accountFn = (CreateIMItemWithAccountLookupFn)dlsym(imdpersistence, "IMDCreateIMItemFromIMDMessageRecordRefWithAccountLookup");
        CreateIMItemWithServiceResolveFn serviceFn = (CreateIMItemWithServiceResolveFn)dlsym(imdpersistence, "IMDCreateIMItemFromIMDMessageRecordRefWithServiceResolve");
        SetDBServerProcessFn setDbFn = (SetDBServerProcessFn)dlsym(imdpersistence, "IMDSetIsRunningInDatabaseServerProcess");

        NSDictionary *payload = @{
            @"guid": guid ?: @"",
            @"dlopen_imdpersistence": @(imdpersistence != NULL),
            @"dlopen_imcore": @(imcore != NULL),
            @"dlopen_imshared": @(imshared != NULL),
            @"symbol_copyMessagesForGUIDs": @(copyFn != NULL),
            @"symbol_createWithAccountLookup": @(accountFn != NULL),
            @"symbol_createWithServiceResolve": @(serviceFn != NULL),
            @"symbol_setDBServerProcess": @(setDbFn != NULL),
            @"query_default": RunQuery(guid, copyFn, accountFn, serviceFn, setDbFn, 0),
            @"query_db_process": RunQuery(guid, copyFn, accountFn, serviceFn, setDbFn, 1),
        };

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
