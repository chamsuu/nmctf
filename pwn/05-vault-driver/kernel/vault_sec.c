#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/seq_file.h>
#include <linux/proc_fs.h>
#include <linux/seqlock.h>
#include <linux/delay.h>
#include <linux/miscdevice.h>
#include <linux/slab.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("PixelVault Security Team");
MODULE_DESCRIPTION("Vault Access Control Driver v1.0");

struct vault_state_t {
    int      locked;
    uint64_t access_count;
    char     last_user[64];
};

static struct vault_state_t g_vault_state = { .locked = 1 };
static DEFINE_SEQLOCK(vault_seqlock);
static uint8_t g_vault_staging[256];

struct vault_request {
    uint32_t door_id;
    uint32_t data_len;
};

#define VAULT_IOC_MAGIC  'V'
#define VAULT_IOC_ACCESS _IOWR(VAULT_IOC_MAGIC, 1, struct vault_request)

static long vault_ioctl(struct file *f, unsigned int cmd, unsigned long arg)
{
    if (cmd != VAULT_IOC_ACCESS) return -ENOTTY;

    struct vault_request __user *ureq = (struct vault_request __user *)arg;
    uint32_t validated_len = 0;

    unsigned int seq = read_seqbegin(&vault_seqlock);
    if (get_user(validated_len, &ureq->data_len))
        return -EFAULT;
    if (read_seqretry(&vault_seqlock, seq))
        goto check;

check:
    if (validated_len > sizeof(g_vault_staging))
        return -EINVAL;

    usleep_range(80000, 120000);

    {
        struct vault_request req;
        if (copy_from_user(&req, ureq, sizeof(req)))
            return -EFAULT;

        if (copy_from_user(g_vault_staging,
                           (uint8_t __user *)arg + sizeof(req),
                           req.data_len))
            return -EFAULT;
    }

    g_vault_state.access_count++;
    return 0;
}

static int vault_proc_show(struct seq_file *m, void *v)
{
    seq_printf(m, "Vault Security Module v1.0\n");
    seq_printf(m, "Module base:    %pK\n", THIS_MODULE->core_layout.base);
    seq_printf(m, "State addr:     %pK\n", &g_vault_state);
    seq_printf(m, "Staging addr:   %pK\n", g_vault_staging);
    seq_printf(m, "Status: %s\n", g_vault_state.locked ? "LOCKED" : "OPEN");
    return 0;
}

static int vault_proc_open(struct inode *i, struct file *f) {
    return single_open(f, vault_proc_show, NULL);
}

static const struct proc_ops vault_proc_ops = {
    .proc_open    = vault_proc_open,
    .proc_read    = seq_read,
    .proc_lseek   = seq_lseek,
    .proc_release = single_release,
};

static const struct file_operations vault_fops = {
    .owner          = THIS_MODULE,
    .unlocked_ioctl = vault_ioctl,
};

static struct miscdevice vault_dev = {
    .minor = MISC_DYNAMIC_MINOR,
    .name  = "vault_sec",
    .fops  = &vault_fops,
    .mode  = 0666,
};

static int __init vault_init(void)
{
    int ret = misc_register(&vault_dev);
    if (ret) return ret;

    proc_create("vault_status", 0444, NULL, &vault_proc_ops);
    pr_info("vault_sec: loaded. Device: /dev/vault_sec\n");
    return 0;
}

static void __exit vault_exit(void)
{
    remove_proc_entry("vault_status", NULL);
    misc_deregister(&vault_dev);
    pr_info("vault_sec: unloaded.\n");
}

module_init(vault_init);
module_exit(vault_exit);